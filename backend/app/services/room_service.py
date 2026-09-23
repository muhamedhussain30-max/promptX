"""
RoomService — creates/manages game rooms and handles player lifecycle.
All writes go to PostgreSQL; hot state (presence, timers) lives in Redis.
"""
import random
import string
import secrets
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import redis.asyncio as aioredis

from app.models.game import Game, GameStatus
from app.models.player import Player, PlayerStatus
from app.database.redis import (
    room_key, room_players_key, room_state_key, player_session_key,
    set_json, get_json, delete_key,
)
from app.services.game_state_machine import assert_transition, can_join, log_transition
from app.config.settings import settings
from app.config.logging import logger


def _generate_room_code(length: int = 6) -> str:
    """Generate an uppercase alphanumeric room code (e.g. X7K92P)."""
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choices(chars, k=length))


def _generate_session_token() -> str:
    return secrets.token_urlsafe(32)


# ── Game / Room ────────────────────────────────────────────────────────────────

async def create_game(
    db: AsyncSession,
    redis: aioredis.Redis,
    host_id: str,
    title: str = "PromptX Prelims",
    max_players: int = 70,
    total_rounds: int = 5,
    round_duration: int = 60,
    max_attempts: int = 3,
) -> Game:
    """Create a new game room and persist initial Redis state."""
    # Ensure unique room code
    for _ in range(10):
        code = _generate_room_code(settings.room_code_length)
        existing = await db.execute(select(Game).where(Game.room_code == code))
        if existing.scalar_one_or_none() is None:
            break

    game = Game(
        title=title,
        room_code=code,
        host_id=host_id,
        max_players=max_players,
        total_rounds=total_rounds,
        round_duration=round_duration,
        max_attempts=max_attempts,
        status=GameStatus.LOBBY,
    )
    db.add(game)
    await db.flush()

    # Store lightweight room metadata in Redis (TTL: 24h)
    await set_json(redis, room_key(code), {
        "game_id": game.id,
        "host_id": host_id,
        "status": GameStatus.LOBBY.value,
        "max_players": max_players,
        "current_round": 0,
        "total_rounds": total_rounds,
        "round_duration": round_duration,
        "max_attempts": max_attempts,
    }, ttl=86400)

    logger.info("game_created", game_id=game.id, room_code=code, host_id=host_id)
    return game


async def get_game_by_code(db: AsyncSession, room_code: str) -> Optional[Game]:
    result = await db.execute(select(Game).where(Game.room_code == room_code.upper()))
    return result.scalar_one_or_none()


async def get_game_by_id(db: AsyncSession, game_id: str) -> Optional[Game]:
    result = await db.execute(select(Game).where(Game.id == game_id))
    return result.scalar_one_or_none()


async def get_player_count(db: AsyncSession, game_id: str) -> int:
    result = await db.execute(
        select(func.count()).where(
            Player.game_id == game_id,
            Player.status != PlayerStatus.ELIMINATED,
        ).execution_options(populate_existing=True)
    )
    return result.scalar_one()


# ── Player joining ─────────────────────────────────────────────────────────────

async def join_game(
    db: AsyncSession,
    redis: aioredis.Redis,
    room_code: str,
    display_name: str,
) -> tuple[Player, str]:
    """
    Add a player to the game.
    Returns (Player, session_token).
    Raises ValueError on invalid join attempt.
    """
    game = await get_game_by_code(db, room_code)
    if game is None:
        raise ValueError(f"Room '{room_code}' not found")

    if not can_join(game.status):
        raise ValueError(f"Game is not accepting new players (status: {game.status})")

    player_count = await get_player_count(db, game.id)
    if player_count >= game.max_players:
        raise ValueError(f"Room is full ({player_count}/{game.max_players})")

    # Check for duplicate name in this game
    dup = await db.execute(
        select(Player).where(
            Player.game_id == game.id,
            Player.display_name == display_name,
        )
    )
    if dup.scalar_one_or_none() is not None:
        raise ValueError(f"Display name '{display_name}' is already taken in this room")

    token = _generate_session_token()
    player = Player(
        game_id=game.id,
        display_name=display_name,
        session_token=token,
        status=PlayerStatus.WAITING,
    )
    db.add(player)
    await db.flush()

    # Update Redis player set
    players_data = await get_json(redis, room_players_key(room_code)) or {}
    players_data[player.id] = {
        "id": player.id,
        "display_name": display_name,
        "status": PlayerStatus.WAITING.value,
        "is_ready": False,
        "total_score": 0,
    }
    await set_json(redis, room_players_key(room_code), players_data, ttl=86400)

    # Store player session
    await set_json(redis, player_session_key(player.id), {
        "player_id": player.id,
        "game_id": game.id,
        "room_code": room_code,
        "display_name": display_name,
    }, ttl=86400)

    logger.info("player_joined", player_id=player.id, display_name=display_name, room_code=room_code)
    return player, token


# ── Player readiness ───────────────────────────────────────────────────────────

async def set_player_ready(
    db: AsyncSession,
    redis: aioredis.Redis,
    player_id: str,
    is_ready: bool,
) -> Player:
    result = await db.execute(select(Player).where(Player.id == player_id))
    player = result.scalar_one_or_none()
    if player is None:
        raise ValueError(f"Player {player_id} not found")

    player.is_ready = is_ready
    player.status = PlayerStatus.READY if is_ready else PlayerStatus.WAITING
    await db.flush()

    # Sync to Redis
    game = await get_game_by_id(db, player.game_id)
    if game:
        players_data = await get_json(redis, room_players_key(game.room_code)) or {}
        if player_id in players_data:
            players_data[player_id]["is_ready"] = is_ready
            players_data[player_id]["status"] = player.status.value
            await set_json(redis, room_players_key(game.room_code), players_data, ttl=86400)

    logger.info("player_ready_changed", player_id=player_id, is_ready=is_ready)
    return player


# ── Game state transitions ─────────────────────────────────────────────────────

async def transition_game_state(
    db: AsyncSession,
    redis: aioredis.Redis,
    game_id: str,
    new_status: GameStatus,
) -> Game:
    game = await get_game_by_id(db, game_id)
    if game is None:
        raise ValueError(f"Game {game_id} not found")

    assert_transition(game.status, new_status)
    log_transition(game_id, game.status, new_status)

    old_status = game.status
    game.status = new_status
    await db.flush()

    # Sync status to Redis room state
    room_state = await get_json(redis, room_state_key(game.room_code)) or {}
    room_state["status"] = new_status.value
    await set_json(redis, room_state_key(game.room_code), room_state, ttl=86400)

    return game


# ── Player helpers ─────────────────────────────────────────────────────────────

async def get_player_by_token(db: AsyncSession, token: str) -> Optional[Player]:
    result = await db.execute(select(Player).where(Player.session_token == token))
    return result.scalar_one_or_none()


async def get_players_in_game(db: AsyncSession, game_id: str) -> list[Player]:
    result = await db.execute(
        select(Player)
        .where(Player.game_id == game_id)
        .order_by(Player.created_at)
        .execution_options(populate_existing=True)
    )
    return list(result.scalars().all())


async def get_active_players_in_game(db: AsyncSession, game_id: str) -> list[Player]:
    """Players who are not eliminated."""
    result = await db.execute(
        select(Player)
        .where(
            Player.game_id == game_id,
            Player.status != PlayerStatus.ELIMINATED,
        )
        .order_by(Player.created_at)
    )
    return list(result.scalars().all())


async def eliminate_player(db: AsyncSession, redis: aioredis.Redis, player_id: str) -> Player:
    result = await db.execute(select(Player).where(Player.id == player_id))
    player = result.scalar_one_or_none()
    if not player:
        raise ValueError(f"Player {player_id} not found")

    player.status = PlayerStatus.ELIMINATED
    await db.flush()

    game = await get_game_by_id(db, player.game_id)
    if game:
        players_data = await get_json(redis, room_players_key(game.room_code)) or {}
        if player_id in players_data:
            players_data[player_id]["status"] = PlayerStatus.ELIMINATED.value
            await set_json(redis, room_players_key(game.room_code), players_data, ttl=86400)

    logger.info("player_eliminated", player_id=player_id, game_id=player.game_id)
    return player


async def advance_player(db: AsyncSession, redis: aioredis.Redis, player_id: str) -> Player:
    result = await db.execute(select(Player).where(Player.id == player_id))
    player = result.scalar_one_or_none()
    if not player:
        raise ValueError(f"Player {player_id} not found")

    player.status = PlayerStatus.ADVANCED
    await db.flush()

    game = await get_game_by_id(db, player.game_id)
    if game:
        players_data = await get_json(redis, room_players_key(game.room_code)) or {}
        if player_id in players_data:
            players_data[player_id]["status"] = PlayerStatus.ADVANCED.value
            await set_json(redis, room_players_key(game.room_code), players_data, ttl=86400)

    logger.info("player_advanced", player_id=player_id, game_id=player.game_id)
    return player
