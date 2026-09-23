"""
RoundService — creates and manages rounds within a game.
The server owns all timers; clients receive authoritative timestamps.
"""
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import redis.asyncio as aioredis

from app.models.round import Round, RoundStatus
from app.models.game import Game, GameStatus
from app.models.challenge import Challenge
from app.models.player import Player, PlayerStatus
from app.database.redis import round_key, room_state_key, set_json, get_json
from app.services.game_state_machine import assert_transition
from app.config.logging import logger


def utcnow() -> datetime:
    # Return naive UTC datetime — SQLite doesn't store timezone info
    return datetime.utcnow()


async def create_round(
    db: AsyncSession,
    game: Game,
    challenge: Challenge,
    round_number: int,
) -> Round:
    """Create a new round record (PENDING status)."""
    rnd = Round(
        game_id=game.id,
        challenge_id=challenge.id,
        round_number=round_number,
        status=RoundStatus.PENDING,
        duration=game.round_duration,
    )
    db.add(rnd)
    await db.flush()
    logger.info("round_created", round_id=rnd.id, round_number=round_number, game_id=game.id)
    return rnd


async def start_round(
    db: AsyncSession,
    redis: aioredis.Redis,
    round_id: str,
    game: Game,
) -> Round:
    """Activate a round and store authoritative timing in Redis."""
    result = await db.execute(select(Round).where(Round.id == round_id))
    rnd = result.scalar_one_or_none()
    if rnd is None:
        raise ValueError(f"Round {round_id} not found")
    if rnd.status != RoundStatus.PENDING:
        raise ValueError(f"Round already started (status: {rnd.status})")

    now = utcnow()
    end_time = now + timedelta(seconds=rnd.duration)

    rnd.status = RoundStatus.ACTIVE
    rnd.started_at = now
    await db.flush()

    # Mark active players as ACTIVE status
    players_result = await db.execute(
        select(Player).where(
            Player.game_id == game.id,
            Player.status.in_([PlayerStatus.READY, PlayerStatus.ADVANCED, PlayerStatus.WAITING])
        )
    )
    for player in players_result.scalars().all():
        player.status = PlayerStatus.ACTIVE
        player.current_round = rnd.round_number

    await db.flush()

    # Store round timing in Redis
    await set_json(redis, round_key(game.room_code, rnd.round_number), {
        "round_id": rnd.id,
        "round_number": rnd.round_number,
        "challenge_id": rnd.challenge_id,
        "started_at": now.isoformat(),
        "ends_at": end_time.isoformat(),
        "duration": rnd.duration,
        "status": RoundStatus.ACTIVE.value,
    }, ttl=rnd.duration + 300)

    # Update room state
    room_state = await get_json(redis, room_state_key(game.room_code)) or {}
    room_state["current_round"] = rnd.round_number
    room_state["round_id"] = rnd.id
    room_state["round_ends_at"] = end_time.isoformat()
    await set_json(redis, room_state_key(game.room_code), room_state, ttl=86400)

    logger.info("round_started", round_id=rnd.id, ends_at=end_time.isoformat())
    return rnd


async def end_round(
    db: AsyncSession,
    redis: aioredis.Redis,
    round_id: str,
    game: Game,
) -> Round:
    """Move a round from ACTIVE → PROCESSING."""
    result = await db.execute(select(Round).where(Round.id == round_id))
    rnd = result.scalar_one_or_none()
    if rnd is None:
        raise ValueError(f"Round {round_id} not found")

    rnd.status = RoundStatus.PROCESSING
    rnd.ended_at = utcnow()
    await db.flush()

    # Update Redis
    rd_data = await get_json(redis, round_key(game.room_code, rnd.round_number)) or {}
    rd_data["status"] = RoundStatus.PROCESSING.value
    await set_json(redis, round_key(game.room_code, rnd.round_number), rd_data, ttl=3600)

    logger.info("round_ended", round_id=rnd.id)
    return rnd


async def complete_round(
    db: AsyncSession,
    redis: aioredis.Redis,
    round_id: str,
    game: Game,
) -> Round:
    """Move a round from PROCESSING → COMPLETED after scoring finishes."""
    result = await db.execute(select(Round).where(Round.id == round_id))
    rnd = result.scalar_one_or_none()
    if rnd is None:
        raise ValueError(f"Round {round_id} not found")

    rnd.status = RoundStatus.COMPLETED
    await db.flush()
    logger.info("round_completed", round_id=rnd.id)
    return rnd


async def get_round_by_id(db: AsyncSession, round_id: str) -> Optional[Round]:
    result = await db.execute(select(Round).where(Round.id == round_id))
    return result.scalar_one_or_none()


async def get_current_round(db: AsyncSession, game_id: str) -> Optional[Round]:
    """Return the most recent non-completed round for a game."""
    result = await db.execute(
        select(Round)
        .where(Round.game_id == game_id)
        .order_by(Round.round_number.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_remaining_time_seconds(redis: aioredis.Redis, room_code: str, round_number: int) -> float:
    """Return authoritative remaining time from Redis. 0 if expired."""
    data = await get_json(redis, round_key(room_code, round_number))
    if data is None:
        return 0.0
    ends_at_str = data.get("ends_at")
    if not ends_at_str:
        return 0.0
    ends_at = datetime.fromisoformat(ends_at_str)
    # Handle both naive and aware datetimes from Redis
    now = utcnow()
    if ends_at.tzinfo is None:
        now = now.replace(tzinfo=None)
    remaining = (ends_at - now).total_seconds()
    return max(0.0, remaining)


async def is_round_accepting_submissions(redis: aioredis.Redis, room_code: str, round_number: int) -> bool:
    remaining = await get_remaining_time_seconds(redis, room_code, round_number)
    data = await get_json(redis, round_key(room_code, round_number))
    if data is None:
        return False
    return remaining > 0 and data.get("status") == RoundStatus.ACTIVE.value
