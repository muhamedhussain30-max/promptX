"""
WebSocket message handlers — one function per ClientEvent.
All background tasks (countdown, timer expiry) open their OWN fresh DB sessions.
Never pass a request-scoped session into an asyncio.create_task.
"""
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from app.websockets.events import ClientEvent
from app.websockets.connection_manager import manager
from app.websockets import event_emitter as emit
from app.models.player import PlayerStatus
from app.models.game import GameStatus
from app.services import (
    set_player_ready, get_players_in_game, get_game_by_id,
    transition_game_state, get_active_players_in_game,
)
from app.services.round_service import get_current_round
from app.services.timer_service import register_timer, cancel_timer, RoundTimer
from app.config.settings import settings
from app.config.logging import logger


def _player_to_dict(player) -> dict:
    return {
        "id": player.id,
        "display_name": player.display_name,
        "status": player.status.value,
        "is_ready": player.is_ready,
        "total_score": player.total_score,
        "rank": player.rank,
    }


async def build_lobby_payload(db: AsyncSession, game) -> dict:
    players = await get_players_in_game(db, game.id)
    return {
        "game_id": game.id,
        "title": game.title,
        "room_code": game.room_code,
        "status": game.status.value,
        "max_players": game.max_players,
        "total_rounds": game.total_rounds,
        "round_duration": game.round_duration,
        "max_attempts": game.max_attempts,
        "players": [_player_to_dict(p) for p in players],
        "player_count": len(players),
    }


# ── Ping ──────────────────────────────────────────────────────────────────────

async def handle_ping(ws, room_code: str, player_id: str, payload: dict, **_) -> None:
    await manager.send_to(ws, "pong", {"timestamp": datetime.now(timezone.utc).isoformat()})


# ── Ready toggle ──────────────────────────────────────────────────────────────

async def handle_ready_toggle(
    ws, room_code: str, player_id: str, payload: dict,
    db: AsyncSession, redis: aioredis.Redis, **_
) -> None:
    is_ready: bool = payload.get("is_ready", True)
    try:
        player = await set_player_ready(db, redis, player_id, is_ready)
        await db.commit()
        # Use fresh session for lobby broadcast to avoid stale ORM cache
        from app.database.base import AsyncSessionLocal
        async with AsyncSessionLocal() as fresh_db:
            game = await get_game_by_id(fresh_db, player.game_id)
            if game:
                lobby = await build_lobby_payload(fresh_db, game)
                await emit.emit_lobby_state(room_code, lobby)
    except Exception as e:
        await emit.emit_error(room_code, player_id, str(e))


# ── Host: start game ──────────────────────────────────────────────────────────

async def handle_host_start_game(
    ws, room_code: str, player_id: str, payload: dict,
    db: AsyncSession, redis: aioredis.Redis, is_host: bool, **_
) -> None:
    if not is_host:
        await emit.emit_error(room_code, player_id, "Only the host can start the game", "UNAUTHORIZED")
        return

    from app.services.room_service import get_game_by_code, get_player_count

    game = await get_game_by_code(db, room_code)
    if not game:
        await emit.emit_error(room_code, player_id, "Game not found")
        return

    player_count = await get_player_count(db, game.id)
    if player_count == 0:
        await emit.emit_error(room_code, player_id, "No players in lobby", "NO_PLAYERS")
        return

    try:
        game = await transition_game_state(db, redis, game.id, GameStatus.COUNTDOWN)
        await db.commit()
        await emit.emit_game_started(room_code, {
            "game_id": game.id,
            "title": game.title,
            "total_rounds": game.total_rounds,
        })
        # Spawn countdown with NO reference to the request db/redis
        game_id = game.id
        asyncio.create_task(_run_countdown_fresh(room_code, game_id))
    except Exception as e:
        logger.error("host_start_game_error", error=str(e))
        await emit.emit_error(room_code, player_id, str(e))


async def _run_countdown_fresh(room_code: str, game_id: str) -> None:
    """
    Run the pre-game countdown using a completely fresh DB session.
    Never receives a session from the caller.
    """
    from app.database.base import AsyncSessionLocal
    from app.database.redis import get_redis as _get_redis

    for i in range(settings.countdown_seconds, 0, -1):
        await emit.emit_countdown(room_code, i)
        await asyncio.sleep(1.0)

    async with AsyncSessionLocal() as db:
        redis = await _get_redis()
        try:
            game = await get_game_by_id(db, game_id)
            if game:
                await _start_next_round(room_code, game, db, redis)
                await db.commit()
        except Exception as e:
            logger.error("countdown_start_round_error", error=str(e))


# ── Host: start round (manual) ────────────────────────────────────────────────

async def handle_host_start_round(
    ws, room_code: str, player_id: str, payload: dict,
    db: AsyncSession, redis: aioredis.Redis, is_host: bool, **_
) -> None:
    if not is_host:
        await emit.emit_error(room_code, player_id, "Only the host can start rounds", "UNAUTHORIZED")
        return

    from app.services.room_service import get_game_by_code
    game = await get_game_by_code(db, room_code)
    if not game:
        return

    await _start_next_round(room_code, game, db, redis)
    await db.commit()


async def _start_next_round(room_code: str, game, db: AsyncSession, redis) -> None:
    """Pick next challenge, create and activate the round, register the server timer."""
    from app.services.round_service import create_round, start_round
    from app.challenges.challenge_service import pick_challenge_for_round

    next_round_number = game.current_round_number + 1
    game.current_round_number = next_round_number

    challenge = await pick_challenge_for_round(db, game)
    rnd = await create_round(db, game, challenge, next_round_number)
    await db.flush()

    game = await transition_game_state(db, redis, game.id, GameStatus.ROUND_ACTIVE)
    rnd = await start_round(db, redis, rnd.id, game)

    round_payload = {
        "round_id": rnd.id,
        "round_number": rnd.round_number,
        "total_rounds": game.total_rounds,
        "ends_at": (rnd.started_at.replace(tzinfo=None) + timedelta(seconds=rnd.duration)).isoformat() if rnd.started_at else None,
        "duration": rnd.duration,
        "challenge": {
            "id": challenge.id,
            "target_description": challenge.target_description,
            "forbidden_words": challenge.forbidden_words,
            "difficulty": challenge.difficulty.value,
            "category": challenge.category.value,
        },
    }
    await emit.emit_round_started(room_code, round_payload)

    register_timer(
        room_code,
        RoundTimer(
            room_code=room_code,
            round_number=rnd.round_number,
            duration=rnd.duration,
            on_tick=_on_timer_tick,
            on_expire=_on_timer_expire,
        ),
    )


# ── Timer callbacks ───────────────────────────────────────────────────────────

async def _on_timer_tick(room_code: str, round_number: int, remaining: float) -> None:
    await emit.emit_timer_tick(room_code, remaining)


async def _on_timer_expire(room_code: str, round_number: int) -> None:
    """Called by the timer background task — always opens a fresh DB session."""
    from app.database.base import AsyncSessionLocal
    from app.database.redis import get_redis as _get_redis
    from app.services.room_service import get_game_by_code
    from app.services.round_service import end_round, get_current_round
    from app.workers.scoring_worker import process_round_scores

    logger.info("round_timer_expired", room_code=room_code, round_number=round_number)

    async with AsyncSessionLocal() as db:
        redis = await _get_redis()
        try:
            game = await get_game_by_code(db, room_code)
            if not game:
                return

            rnd = await get_current_round(db, game.id)
            if not rnd:
                return

            await emit.emit_round_ended(room_code, round_number)
            await end_round(db, redis, rnd.id, game)
            game = await transition_game_state(db, redis, game.id, GameStatus.ROUND_PROCESSING)
            await emit.emit_round_processing(room_code)
            await db.commit()

            round_id = rnd.id
            game_id = game.id
        except Exception as e:
            logger.error("timer_expire_error", error=str(e))
            return

    # Score in a separate task/session
    asyncio.create_task(process_round_scores(room_code, game_id, round_id))


# ── Host: end round early ─────────────────────────────────────────────────────

async def handle_host_end_round(
    ws, room_code: str, player_id: str, payload: dict,
    db: AsyncSession, redis: aioredis.Redis, is_host: bool, **_
) -> None:
    if not is_host:
        await emit.emit_error(room_code, player_id, "Unauthorized", "UNAUTHORIZED")
        return

    cancel_timer(room_code)

    from app.services.room_service import get_game_by_code
    from app.services.round_service import end_round
    from app.workers.scoring_worker import process_round_scores

    game = await get_game_by_code(db, room_code)
    if not game:
        return
    rnd = await get_current_round(db, game.id)
    if not rnd:
        return

    await emit.emit_round_ended(room_code, rnd.round_number)
    await end_round(db, redis, rnd.id, game)
    game = await transition_game_state(db, redis, game.id, GameStatus.ROUND_PROCESSING)
    await emit.emit_round_processing(room_code)
    await db.commit()

    asyncio.create_task(process_round_scores(room_code, game.id, rnd.id))


# ── Host: shortlist ───────────────────────────────────────────────────────────

async def handle_host_shortlist(
    ws, room_code: str, player_id: str, payload: dict,
    db: AsyncSession, redis: aioredis.Redis, is_host: bool, **_
) -> None:
    if not is_host:
        await emit.emit_error(room_code, player_id, "Unauthorized", "UNAUTHORIZED")
        return

    advancing_count: int = payload.get("advancing_count", 40)
    manual_ids: Optional[list] = payload.get("advancing_player_ids")

    from app.services.room_service import get_game_by_code
    from app.services.shortlist_service import build_round_leaderboard, apply_shortlist

    game = await get_game_by_code(db, room_code)
    rnd = await get_current_round(db, game.id) if game else None
    if not game or not rnd:
        return

    leaderboard = await build_round_leaderboard(db, game.id, rnd.id)

    if manual_ids:
        advance_set = set(manual_ids)
        advancing_count = len(manual_ids)
        leaderboard = (
            [e for e in leaderboard if e["player_id"] in advance_set] +
            [e for e in leaderboard if e["player_id"] not in advance_set]
        )

    result = await apply_shortlist(db, redis, game.id, rnd.id, advancing_count, leaderboard)
    game = await transition_game_state(db, redis, game.id, GameStatus.SHORTLISTING)
    await db.commit()

    await emit.emit_shortlist(room_code, {
        "advanced": result["advanced"],
        "eliminated": result["eliminated"],
    })


# ── Host: next round ──────────────────────────────────────────────────────────

async def handle_host_next_round(
    ws, room_code: str, player_id: str, payload: dict,
    db: AsyncSession, redis: aioredis.Redis, is_host: bool, **_
) -> None:
    if not is_host:
        await emit.emit_error(room_code, player_id, "Unauthorized", "UNAUTHORIZED")
        return

    from app.services.room_service import get_game_by_code

    game = await get_game_by_code(db, room_code)
    if not game:
        return

    if game.current_round_number >= game.total_rounds:
        await handle_host_end_game(ws, room_code, player_id, payload, db, redis, is_host)
        return

    game = await transition_game_state(db, redis, game.id, GameStatus.NEXT_ROUND)
    await emit.emit_next_round(room_code, game.current_round_number + 1)
    game_id = game.id
    await db.commit()

    asyncio.create_task(_run_countdown_fresh(room_code, game_id))


# ── Host: end game ────────────────────────────────────────────────────────────

async def handle_host_end_game(
    ws, room_code: str, player_id: str, payload: dict,
    db: AsyncSession, redis: aioredis.Redis, is_host: bool, **_
) -> None:
    if not is_host:
        await emit.emit_error(room_code, player_id, "Unauthorized", "UNAUTHORIZED")
        return

    cancel_timer(room_code)

    from app.services.room_service import get_game_by_code

    game = await get_game_by_code(db, room_code)
    if not game:
        return

    game = await transition_game_state(db, redis, game.id, GameStatus.FINISHED)
    await db.commit()

    from app.services.shortlist_service import build_round_leaderboard
    rnd = await get_current_round(db, game.id)
    winners = []
    if rnd:
        lb = await build_round_leaderboard(db, game.id, rnd.id)
        winners = lb[:3]

    await emit.emit_game_finished(room_code)
    await emit.emit_winner_announced(room_code, winners)


# ── Host: remove player ───────────────────────────────────────────────────────

async def handle_host_remove_player(
    ws, room_code: str, player_id: str, payload: dict,
    db: AsyncSession, redis: aioredis.Redis, is_host: bool, **_
) -> None:
    if not is_host:
        await emit.emit_error(room_code, player_id, "Unauthorized", "UNAUTHORIZED")
        return

    target_id: str = payload.get("player_id", "")
    from app.services.room_service import eliminate_player
    from sqlalchemy import select
    from app.models.player import Player

    result = await db.execute(select(Player).where(Player.id == target_id))
    target = result.scalar_one_or_none()
    if not target:
        return

    await eliminate_player(db, redis, target_id)
    await db.commit()
    await emit.emit_player_removed(room_code, target_id)


# ── Dispatch table ────────────────────────────────────────────────────────────

HANDLERS = {
    ClientEvent.PING:               handle_ping,
    ClientEvent.READY_TOGGLE:       handle_ready_toggle,
    ClientEvent.HOST_START_GAME:    handle_host_start_game,
    ClientEvent.HOST_START_ROUND:   handle_host_start_round,
    ClientEvent.HOST_END_ROUND:     handle_host_end_round,
    ClientEvent.HOST_SHORTLIST:     handle_host_shortlist,
    ClientEvent.HOST_NEXT_ROUND:    handle_host_next_round,
    ClientEvent.HOST_END_GAME:      handle_host_end_game,
    ClientEvent.HOST_REMOVE_PLAYER: handle_host_remove_player,
}
