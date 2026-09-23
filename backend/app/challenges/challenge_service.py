"""
ChallengeService — manages the challenge database and round assignment.
Ensures no challenge is reused within the same game session.
"""
import random
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.challenge import Challenge, Difficulty
from app.models.round import Round
from app.models.game import Game
from app.config.logging import logger


async def get_all_challenges(db: AsyncSession, active_only: bool = True) -> list[Challenge]:
    q = select(Challenge)
    if active_only:
        q = q.where(Challenge.is_active == True)  # noqa: E712
    result = await db.execute(q)
    return list(result.scalars().all())


async def get_challenge_by_id(db: AsyncSession, challenge_id: str) -> Optional[Challenge]:
    result = await db.execute(select(Challenge).where(Challenge.id == challenge_id))
    return result.scalar_one_or_none()


async def get_used_challenge_ids(db: AsyncSession, game_id: str) -> set[str]:
    """Return IDs of challenges already used in this game."""
    result = await db.execute(
        select(Round.challenge_id).where(Round.game_id == game_id)
    )
    return {row[0] for row in result.all()}


async def pick_challenge_for_round(
    db: AsyncSession,
    game: Game,
    difficulty: Optional[Difficulty] = None,
) -> Challenge:
    """
    Select a challenge that hasn't been used in this game yet.
    Falls back to any active challenge if all have been used.
    """
    used_ids = await get_used_challenge_ids(db, game.id)

    q = select(Challenge).where(Challenge.is_active == True)  # noqa: E712
    if difficulty:
        q = q.where(Challenge.difficulty == difficulty)

    result = await db.execute(q)
    all_challenges = list(result.scalars().all())

    # Prefer unused challenges
    unused = [c for c in all_challenges if c.id not in used_ids]
    pool = unused if unused else all_challenges

    if not pool:
        raise ValueError("No challenges available in the database. Run seed first.")

    chosen = random.choice(pool)
    logger.info(
        "challenge_picked",
        challenge_id=chosen.id,
        title=chosen.title,
        game_id=game.id,
        round_number=game.current_round_number + 1,
    )
    return chosen


async def create_challenge(db: AsyncSession, data: dict) -> Challenge:
    challenge = Challenge(**data)
    db.add(challenge)
    await db.flush()
    return challenge
