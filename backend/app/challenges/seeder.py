"""
Database seeder — idempotent, safe to run multiple times.
Only inserts challenges that don't already exist (matched by title).
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.challenge import Challenge
from app.challenges.seed_data import SEED_CHALLENGES
from app.config.logging import logger


async def seed_challenges(db: AsyncSession) -> int:
    """
    Insert all seed challenges that aren't already present.
    Returns the number of new challenges inserted.
    """
    inserted = 0

    for data in SEED_CHALLENGES:
        # Check by title to make seeding idempotent
        existing = await db.execute(
            select(Challenge).where(Challenge.title == data["title"])
        )
        if existing.scalar_one_or_none() is not None:
            continue

        challenge = Challenge(
            title=data["title"],
            target_description=data["target_description"],
            category=data["category"],
            difficulty=data["difficulty"],
            forbidden_words=data["forbidden_words"],
            required_objects=data["required_objects"],
            required_attributes=data["required_attributes"],
            required_scene=data["required_scene"],
            required_relationships=data["required_relationships"],
        )
        db.add(challenge)
        inserted += 1

    if inserted:
        await db.flush()
        logger.info("challenges_seeded", count=inserted)
    else:
        logger.info("challenges_already_seeded")

    return inserted


async def run_seed() -> None:
    """Entry point for running seed from CLI or startup."""
    from app.database.base import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        count = await seed_challenges(db)
        await db.commit()
        print(f"Seeded {count} new challenges.")
