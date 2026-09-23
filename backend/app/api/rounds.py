"""
Round routes — prompt validation, image generation, final submission.
All business logic delegates to services; routes only handle HTTP concerns.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import redis.asyncio as aioredis

from app.database.base import get_db
from app.database.redis import get_redis
from app.models.player import Player
from app.models.round import Round, RoundStatus
from app.models.game import Game
from app.schemas.common import APIResponse
from app.schemas.submission import (
    ValidatePromptRequest, ValidatePromptResponse,
    GenerateImageRequest, GenerateImageResponse,
    FinalSubmitRequest, SubmissionOut,
)
from app.schemas.score import ScoreBreakdown
from app.services.prompt_validator import validate_prompt
from app.services.submission_service import (
    validate_and_create_submission,
    request_image_generation,
    set_final_submission,
)
from app.services.round_service import is_round_accepting_submissions
from app.api.deps import get_current_player, get_redis_dep
from app.websockets import event_emitter as emit

router = APIRouter()


async def _get_round_or_404(db: AsyncSession, round_id: str) -> Round:
    result = await db.execute(select(Round).where(Round.id == round_id))
    rnd = result.scalar_one_or_none()
    if not rnd:
        raise HTTPException(status_code=404, detail="Round not found")
    return rnd


async def _get_game_for_round(db: AsyncSession, round_id: str) -> Game:
    rnd = await _get_round_or_404(db, round_id)
    result = await db.execute(select(Game).where(Game.id == rnd.game_id))
    game = result.scalar_one_or_none()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return game


# ── POST /api/rounds/{round_id}/validate-prompt ───────────────────────────────

@router.post("/{round_id}/validate-prompt", response_model=APIResponse[ValidatePromptResponse])
async def validate_prompt_route(
    round_id: str,
    body: ValidatePromptRequest,
    db: AsyncSession = Depends(get_db),
    player: Player = Depends(get_current_player),
):
    """
    Server-side prompt validation. Returns immediately with result.
    Does NOT create a submission record — that happens at generate.
    """
    rnd = await _get_round_or_404(db, round_id)
    if rnd.status != RoundStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Round is not active")

    # Fetch challenge's forbidden words
    from app.models.challenge import Challenge
    ch_result = await db.execute(select(Challenge).where(Challenge.id == rnd.challenge_id))
    challenge = ch_result.scalar_one_or_none()
    if not challenge:
        raise HTTPException(status_code=500, detail="Challenge not found")

    result = validate_prompt(body.prompt, challenge.forbidden_words)
    return APIResponse(data=ValidatePromptResponse(
        is_valid=result.is_valid,
        normalized_prompt=result.normalized_prompt,
        forbidden_words_detected=result.forbidden_words_detected,
        message=result.message,
    ))


# ── POST /api/rounds/{round_id}/generate ─────────────────────────────────────

@router.post("/{round_id}/generate", response_model=APIResponse[GenerateImageResponse], status_code=202)
async def generate_image(
    round_id: str,
    body: GenerateImageRequest,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis_dep),
    player: Player = Depends(get_current_player),
):
    """
    Validate prompt server-side, create submission record, queue image generation.
    Returns immediately with submission_id; image arrives via WebSocket.
    """
    try:
        submission = await validate_and_create_submission(
            db, redis, player.id, round_id, body.prompt
        )

        if not submission.is_valid:
            await db.commit()
            return APIResponse(
                success=False,
                data=GenerateImageResponse(
                    submission_id=submission.id,
                    status="rejected",
                    message=f"Prompt rejected: {', '.join(submission.validation_errors or [])}",
                ),
                message="Prompt contains forbidden words",
            )

        # Queue image generation
        submission = await request_image_generation(db, redis, submission.id, player.id)
        await db.commit()

        # The image worker will emit image_generation_started and image_generated via WebSocket
        return APIResponse(data=GenerateImageResponse(
            submission_id=submission.id,
            status="queued",
            message="Image generation queued. You'll receive it via WebSocket.",
        ))

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── GET /api/rounds/{round_id}/my-score ──────────────────────────────────────

@router.get("/{round_id}/my-score", response_model=APIResponse[ScoreBreakdown])
async def get_my_score(
    round_id: str,
    db: AsyncSession = Depends(get_db),
    player: Player = Depends(get_current_player),
):
    """
    Return the player's scored breakdown for their final submission.
    Exposes the full rubric including per-concept results (label+result only).
    Returns 404 until scoring completes.
    """
    from app.models.score import Score
    from app.models.submission import Submission

    sub_result = await db.execute(
        select(Submission).where(
            Submission.round_id == round_id,
            Submission.player_id == player.id,
            Submission.is_final == True,  # noqa: E712
        )
    )
    submission = sub_result.scalar_one_or_none()
    if not submission:
        raise HTTPException(status_code=404, detail="No final submission found")

    score_result = await db.execute(
        select(Score).where(Score.submission_id == submission.id)
    )
    score = score_result.scalar_one_or_none()
    if not score:
        raise HTTPException(status_code=404, detail="Score not yet ready — try again shortly")

    bd = score.accuracy_breakdown or {}
    breakdown = ScoreBreakdown(
        total=score.total,
        match_score=bd.get("match_score", score.accuracy * 2),
        creativity_100=bd.get("creativity_100", score.creativity * 10),
        speed_100=bd.get("speed_100", score.speed * 10),
        efficiency_100=bd.get("efficiency_100", score.efficiency * 10),
        accuracy=score.accuracy,
        compliance=score.compliance,
        creativity=score.creativity,
        speed=score.speed,
        efficiency=score.efficiency,
        accuracy_breakdown=score.accuracy_breakdown,
        image_url=submission.image_url,
        raw_prompt=submission.raw_prompt,
    )
    return APIResponse(data=breakdown)

@router.post("/{round_id}/submit", response_model=APIResponse[SubmissionOut])
async def final_submit(
    round_id: str,
    body: FinalSubmitRequest,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis_dep),
    player: Player = Depends(get_current_player),
):
    """
    Mark a generated submission as the player's final entry for this round.
    Can be called multiple times to switch the final selection.
    """
    try:
        submission = await set_final_submission(db, redis, body.submission_id, player.id, round_id)
        await db.commit()

        game = await _get_game_for_round(db, round_id)
        await emit.emit_submission_completed(game.room_code, player.id, submission.id)

        return APIResponse(data=SubmissionOut.model_validate(submission), message="Submission recorded")

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
