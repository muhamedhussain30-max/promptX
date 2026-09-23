"""
Challenge routes — list, create, seed (host only for mutations).
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.base import get_db
from app.models.challenge import Challenge, Difficulty, ChallengeCategory
from app.challenges.challenge_service import get_all_challenges, get_challenge_by_id
from app.challenges.seeder import seed_challenges
from app.schemas.common import APIResponse
from app.api.deps import get_current_host

router = APIRouter()


class ChallengeOut(BaseModel):
    id: str
    title: str
    target_description: str
    category: ChallengeCategory
    difficulty: Difficulty
    forbidden_words: list[str]
    # Evaluation fields deliberately excluded from this schema

    model_config = {"from_attributes": True}


class ChallengeCreate(BaseModel):
    title: str
    target_description: str
    category: ChallengeCategory
    difficulty: Difficulty
    forbidden_words: list[str]
    required_objects: list[str] = []
    required_attributes: list[str] = []
    required_scene: list[str] = []
    required_relationships: list[str] = []


@router.get("", response_model=APIResponse[list[ChallengeOut]])
async def list_challenges(db: AsyncSession = Depends(get_db)):
    challenges = await get_all_challenges(db)
    return APIResponse(data=[ChallengeOut.model_validate(c) for c in challenges])


@router.get("/{challenge_id}", response_model=APIResponse[ChallengeOut])
async def get_challenge(challenge_id: str, db: AsyncSession = Depends(get_db)):
    challenge = await get_challenge_by_id(db, challenge_id)
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")
    return APIResponse(data=ChallengeOut.model_validate(challenge))


@router.post("", response_model=APIResponse[ChallengeOut], status_code=201)
async def create_challenge(
    body: ChallengeCreate,
    db: AsyncSession = Depends(get_db),
    host=Depends(get_current_host),
):
    challenge = Challenge(
        title=body.title,
        target_description=body.target_description,
        category=body.category,
        difficulty=body.difficulty,
        forbidden_words=body.forbidden_words,
        required_objects=body.required_objects,
        required_attributes=body.required_attributes,
        required_scene=body.required_scene,
        required_relationships=body.required_relationships,
    )
    db.add(challenge)
    await db.flush()
    await db.commit()
    return APIResponse(data=ChallengeOut.model_validate(challenge), message="Challenge created")


@router.post("/seed", response_model=APIResponse)
async def seed(
    db: AsyncSession = Depends(get_db),
    host=Depends(get_current_host),
):
    """Run the seed data importer (idempotent)."""
    count = await seed_challenges(db)
    await db.commit()
    return APIResponse(message=f"Seeded {count} new challenges")
