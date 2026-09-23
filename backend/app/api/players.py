"""
Player routes — ready state, score, submission history.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import redis.asyncio as aioredis

from app.database.base import get_db
from app.database.redis import get_redis
from app.models.player import Player
from app.models.score import Score
from app.schemas.common import APIResponse
from app.schemas.player import PlayerOut, PlayerReadyToggle
from app.schemas.score import ScoreBreakdown
from app.schemas.submission import SubmissionOut
from app.services.room_service import set_player_ready, get_game_by_id
from app.services.submission_service import get_player_submissions
from app.api.deps import get_current_player, get_redis_dep
from app.websockets import event_emitter as emit

router = APIRouter()


@router.get("/me", response_model=APIResponse[PlayerOut])
async def get_me(player: Player = Depends(get_current_player)):
    return APIResponse(data=PlayerOut.model_validate(player))


@router.post("/me/ready", response_model=APIResponse[PlayerOut])
async def toggle_ready(
    body: PlayerReadyToggle,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis_dep),
    player: Player = Depends(get_current_player),
):
    updated = await set_player_ready(db, redis, player.id, body.is_ready)
    await db.commit()

    # Use a FRESH session to query lobby so we never get stale ORM cache
    from app.database.base import AsyncSessionLocal
    async with AsyncSessionLocal() as fresh_db:
        game = await get_game_by_id(fresh_db, updated.game_id)
        if game:
            from app.websockets.handlers import build_lobby_payload
            lobby = await build_lobby_payload(fresh_db, game)
            await emit.emit_lobby_state(game.room_code, lobby)

    return APIResponse(data=PlayerOut.model_validate(updated))


@router.get("/{player_id}/score", response_model=APIResponse[list[ScoreBreakdown]])
async def get_player_scores(
    player_id: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Score).where(Score.player_id == player_id).order_by(Score.created_at)
    )
    scores = result.scalars().all()
    return APIResponse(data=[ScoreBreakdown.model_validate(s) for s in scores])


@router.get("/{player_id}/submissions/{round_id}", response_model=APIResponse[list[SubmissionOut]])
async def get_submissions(
    player_id: str,
    round_id: str,
    db: AsyncSession = Depends(get_db),
    player: Player = Depends(get_current_player),
):
    # Players can only view their own submissions
    if player.id != player_id:
        raise HTTPException(status_code=403, detail="Cannot view other player's submissions")

    submissions = await get_player_submissions(db, player_id, round_id)
    return APIResponse(data=[SubmissionOut.model_validate(s) for s in submissions])
