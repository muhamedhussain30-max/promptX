"""
Game routes — create, join, manage contest rooms.
"""
import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import redis.asyncio as aioredis

from app.database.base import get_db
from app.database.redis import get_redis
from app.models.game import Game, GameStatus
from app.models.player import Player, PlayerStatus
from app.models.score import LeaderboardEntry
from app.schemas.common import APIResponse
from app.schemas.game import (
    GameCreate, GameOut, GameSummary, ShortlistConfig, AdvancementDecision
)
from app.schemas.player import PlayerJoin, PlayerJoinResponse, PlayerOut
from app.schemas.score import LeaderboardOut, LeaderboardEntryOut
from app.services.room_service import (
    create_game, get_game_by_code, get_game_by_id,
    join_game, get_players_in_game, get_active_players_in_game,
    get_player_count, transition_game_state,
    eliminate_player, advance_player,
)
from app.services.shortlist_service import build_round_leaderboard, apply_shortlist
from app.services.round_service import get_current_round
from app.api.deps import get_current_host, get_current_player, get_redis_dep
from app.websockets import event_emitter as emit

router = APIRouter()


# ── POST /api/games — create a new game room ──────────────────────────────────

@router.post("", response_model=APIResponse[GameOut], status_code=201)
async def create_new_game(
    body: GameCreate,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis_dep),
    host=Depends(get_current_host),
):
    game = await create_game(
        db, redis,
        host_id=host.id,
        title=body.title,
        max_players=body.max_players,
        total_rounds=body.total_rounds,
        round_duration=body.round_duration,
        max_attempts=body.max_attempts,
    )
    await db.commit()
    return APIResponse(data=GameOut.model_validate(game), message="Game created", success=True)


# ── GET /api/games/{room_code} — fetch game state ─────────────────────────────

@router.get("/{room_code}", response_model=APIResponse[GameSummary])
async def get_game(room_code: str, db: AsyncSession = Depends(get_db)):
    game = await get_game_by_code(db, room_code.upper())
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    player_count = await get_player_count(db, game.id)
    summary = GameSummary(
        id=game.id,
        title=game.title,
        room_code=game.room_code,
        status=game.status,
        player_count=player_count,
        max_players=game.max_players,
        current_round_number=game.current_round_number,
        total_rounds=game.total_rounds,
    )
    return APIResponse(data=summary)


# ── POST /api/games/{room_code}/join — player joins lobby ────────────────────

@router.post("/{room_code}/join", response_model=APIResponse[PlayerJoinResponse], status_code=201)
async def join_game_room(
    room_code: str,
    body: PlayerJoin,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis_dep),
):
    try:
        player, token = await join_game(db, redis, room_code.upper(), body.display_name)
        await db.commit()

        # Broadcast updated lobby_state using a FRESH session (avoids stale ORM cache)
        from app.database.base import AsyncSessionLocal
        async with AsyncSessionLocal() as fresh_db:
            fresh_game = await get_game_by_code(fresh_db, room_code.upper())
            if fresh_game:
                from app.websockets.handlers import build_lobby_payload
                lobby = await build_lobby_payload(fresh_db, fresh_game)
                await emit.emit_lobby_state(fresh_game.room_code, lobby)
                await emit.emit_player_joined(fresh_game.room_code, {
                    "id": player.id,
                    "display_name": player.display_name,
                    "status": player.status.value,
                    "is_ready": player.is_ready,
                    "total_score": player.total_score,
                })

        return APIResponse(data=PlayerJoinResponse(
            player_id=player.id,
            session_token=token,
            game_id=player.game_id,
            room_code=room_code.upper(),
            display_name=player.display_name,
        ), message="Joined successfully", status_code=201)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── GET /api/games/{room_code}/players — list players ────────────────────────

@router.get("/{room_code}/players", response_model=APIResponse[list[PlayerOut]])
async def list_players(
    room_code: str,
    db: AsyncSession = Depends(get_db),
    host=Depends(get_current_host),
):
    game = await get_game_by_code(db, room_code.upper())
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    players = await get_players_in_game(db, game.id)
    return APIResponse(data=[PlayerOut.model_validate(p) for p in players])


# ── POST /api/games/{game_id}/start — host starts the game ───────────────────

@router.post("/{game_id}/start", response_model=APIResponse)
async def start_game(
    game_id: str,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis_dep),
    host=Depends(get_current_host),
):
    import asyncio
    game = await get_game_by_id(db, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    if game.host_id != host.id:
        raise HTTPException(status_code=403, detail="Not your game")
    player_count = await get_player_count(db, game.id)
    if player_count == 0:
        raise HTTPException(status_code=400, detail="No players in lobby")
    try:
        game = await transition_game_state(db, redis, game.id, GameStatus.COUNTDOWN)
        await db.commit()
        await emit.emit_game_started(game.room_code, {
            "game_id": game.id, "title": game.title, "total_rounds": game.total_rounds,
        })
        # Run countdown + start round (same path as WS host_start_game)
        from app.websockets.handlers import _run_countdown_fresh
        asyncio.create_task(_run_countdown_fresh(game.room_code, game.id))
        return APIResponse(message="Game started")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── GET /api/games/{game_id}/leaderboard ─────────────────────────────────────

@router.get("/{game_id}/leaderboard", response_model=APIResponse[LeaderboardOut])
async def get_leaderboard(
    game_id: str,
    db: AsyncSession = Depends(get_db),
):
    game = await get_game_by_id(db, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    rnd = await get_current_round(db, game_id)
    if not rnd:
        raise HTTPException(status_code=404, detail="No round data yet")

    entries = await build_round_leaderboard(db, game_id, rnd.id)

    lb_entries = [
        LeaderboardEntryOut(
            rank=e["rank"],
            player_id=e["player_id"],
            display_name=e["display_name"],
            round_score=e["round_score"],
            cumulative_score=e["cumulative_score"],
            is_advanced=e["is_advanced"],
            accuracy=e["accuracy"],
            speed=e["speed"],
        )
        for e in entries
    ]
    return APIResponse(data=LeaderboardOut(
        game_id=game_id,
        round_number=rnd.round_number,
        entries=lb_entries,
    ))


# ── POST /api/games/{game_id}/shortlist ───────────────────────────────────────

@router.post("/{game_id}/shortlist", response_model=APIResponse)
async def shortlist_players(
    game_id: str,
    body: ShortlistConfig,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis_dep),
    host=Depends(get_current_host),
):
    game = await get_game_by_id(db, game_id)
    if not game or game.host_id != host.id:
        raise HTTPException(status_code=403, detail="Not your game")

    rnd = await get_current_round(db, game_id)
    if not rnd:
        raise HTTPException(status_code=404, detail="No current round")

    active_players = await get_active_players_in_game(db, game_id)
    total = len(active_players)

    if body.method == "percent":
        advancing_count = max(1, int(total * body.value / 100))
    else:
        advancing_count = min(body.value, total)

    result = await apply_shortlist(db, redis, game_id, rnd.id, advancing_count)
    game = await transition_game_state(db, redis, game_id, GameStatus.SHORTLISTING)
    await db.commit()

    await emit.emit_shortlist(game.room_code, {
        "advanced": result["advanced"],
        "eliminated": result["eliminated"],
    })
    return APIResponse(message=f"Shortlisted: {len(result['advanced'])} advancing, {len(result['eliminated'])} eliminated")


# ── POST /api/games/{game_id}/next-round ─────────────────────────────────────

@router.post("/{game_id}/next-round", response_model=APIResponse)
async def next_round(
    game_id: str,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis_dep),
    host=Depends(get_current_host),
):
    game = await get_game_by_id(db, game_id)
    if not game or game.host_id != host.id:
        raise HTTPException(status_code=403, detail="Not your game")

    game = await transition_game_state(db, redis, game_id, GameStatus.NEXT_ROUND)
    await db.commit()
    await emit.emit_next_round(game.room_code, game.current_round_number + 1)
    return APIResponse(message="Next round initiated")


# ── POST /api/games/{game_id}/end ─────────────────────────────────────────────

@router.post("/{game_id}/end", response_model=APIResponse)
async def end_game(
    game_id: str,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis_dep),
    host=Depends(get_current_host),
):
    game = await get_game_by_id(db, game_id)
    if not game or game.host_id != host.id:
        raise HTTPException(status_code=403, detail="Not your game")

    game = await transition_game_state(db, redis, game_id, GameStatus.FINISHED)
    await db.commit()
    await emit.emit_game_finished(game.room_code)
    return APIResponse(message="Game ended")
