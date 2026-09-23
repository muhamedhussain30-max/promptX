"""
SubmissionService — handles prompt validation, image-gen queueing, and final submit.
The server is authoritative: it re-validates before any image is generated,
and re-checks attempt limits and round status.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import redis.asyncio as aioredis

from app.models.submission import Submission
from app.models.player import Player, PlayerStatus
from app.models.round import Round, RoundStatus
from app.models.challenge import Challenge
from app.models.game import Game
from app.services.prompt_validator import validate_prompt
from app.services.round_service import is_round_accepting_submissions
from app.database.redis import push_queue, image_queue_key
from app.config.logging import logger


def utcnow() -> datetime:
    # Naive UTC — matches SQLite storage
    return datetime.utcnow()


async def _get_attempt_count(db: AsyncSession, player_id: str, round_id: str) -> int:
    result = await db.execute(
        select(func.count())
        .where(Submission.player_id == player_id, Submission.round_id == round_id)
    )
    return result.scalar_one()


async def validate_and_create_submission(
    db: AsyncSession,
    redis: aioredis.Redis,
    player_id: str,
    round_id: str,
    raw_prompt: str,
) -> Submission:
    """
    Server-side validation + submission record creation.
    Raises ValueError for any rule violation.
    """
    # ── Fetch round + challenge ────────────────────────────────────────────────
    round_result = await db.execute(select(Round).where(Round.id == round_id))
    rnd = round_result.scalar_one_or_none()
    if not rnd:
        raise ValueError("Round not found")
    if rnd.status != RoundStatus.ACTIVE:
        raise ValueError("Round is not accepting submissions")

    challenge_result = await db.execute(
        select(Challenge).where(Challenge.id == rnd.challenge_id)
    )
    challenge = challenge_result.scalar_one_or_none()
    if not challenge:
        raise ValueError("Challenge not found")

    # ── Fetch game to check attempt limit ─────────────────────────────────────
    game_result = await db.execute(select(Game).where(Game.id == rnd.game_id))
    game = game_result.scalar_one_or_none()
    if not game:
        raise ValueError("Game not found")

    # ── Verify round is still accepting (server timer + 2s grace) ─────────────
    accepting = await is_round_accepting_submissions(redis, game.room_code, rnd.round_number)
    if not accepting:
        if rnd.status != RoundStatus.ACTIVE:
            raise ValueError("Round has ended — submissions are closed")
        # Redis key missing after restart — trust DB status (ACTIVE = still open)

    # ── Enforce server-side deadline with explicit 2-second grace ─────────────
    if rnd.started_at:
        now_naive = datetime.utcnow()
        started_naive = rnd.started_at.replace(tzinfo=None)
        elapsed_s = (now_naive - started_naive).total_seconds()
        limit_with_grace = rnd.duration + 2
        if elapsed_s > limit_with_grace:
            raise ValueError(
                f"Submission rejected: round ended {int(elapsed_s - rnd.duration)}s ago "
                f"(limit {rnd.duration}s + 2s grace)"
            )

    # ── Check attempt limit ────────────────────────────────────────────────────
    attempt_count = await _get_attempt_count(db, player_id, round_id)
    if attempt_count >= game.max_attempts:
        raise ValueError(f"Maximum attempts reached ({game.max_attempts})")

    # ── One-valid-final enforcement: if a final submission already exists, block new generate ──
    existing_final = await db.execute(
        select(func.count()).where(
            Submission.player_id == player_id,
            Submission.round_id == round_id,
            Submission.is_final == True,  # noqa: E712
        )
    )
    if existing_final.scalar_one() > 0:
        raise ValueError("You have already submitted your final image for this round")

    # ── Validate player eligibility ────────────────────────────────────────────
    player_result = await db.execute(select(Player).where(Player.id == player_id))
    player = player_result.scalar_one_or_none()
    if not player:
        raise ValueError("Player not found")
    if player.status == PlayerStatus.ELIMINATED:
        raise ValueError("Eliminated players cannot submit")

    # ── Run authoritative prompt validation ────────────────────────────────────
    validation = validate_prompt(raw_prompt, challenge.forbidden_words)

    attempt_number = attempt_count + 1

    # Calculate submission time from round start
    submission_time_ms: Optional[int] = None
    if rnd.started_at:
        # Strip tzinfo from both sides — SQLite/SQLAlchemy can return mixed aware/naive
        now_naive = datetime.utcnow()
        started_naive = rnd.started_at.replace(tzinfo=None)
        elapsed = (now_naive - started_naive).total_seconds()
        submission_time_ms = int(max(0, elapsed) * 1000)

    # ── Create submission record ───────────────────────────────────────────────
    submission = Submission(
        round_id=round_id,
        player_id=player_id,
        attempt_number=attempt_number,
        raw_prompt=raw_prompt,
        normalized_prompt=validation.normalized_prompt,
        is_valid=validation.is_valid,
        validation_errors=[f"Forbidden word: {w}" for w in validation.forbidden_words_detected],
        submission_time_ms=submission_time_ms,
        is_suspicious=validation.suspicious,
        suspicious_reason=validation.suspicious_reason,
    )
    db.add(submission)
    await db.flush()

    # Log suspicious activity
    if validation.suspicious:
        logger.warning(
            "suspicious_submission",
            player_id=player_id,
            reason=validation.suspicious_reason,
            prompt=raw_prompt[:200],
        )

    logger.info(
        "submission_created",
        submission_id=submission.id,
        player_id=player_id,
        is_valid=validation.is_valid,
        attempt=attempt_number,
    )

    return submission


async def request_image_generation(
    db: AsyncSession,
    redis: aioredis.Redis,
    submission_id: str,
    player_id: str,
) -> Submission:
    """
    Queue an image-generation job for a valid submission.
    Raises ValueError if submission is invalid or not owned by the player.
    """
    result = await db.execute(select(Submission).where(Submission.id == submission_id))
    submission = result.scalar_one_or_none()
    if not submission:
        raise ValueError("Submission not found")
    if submission.player_id != player_id:
        raise ValueError("Not your submission")
    if not submission.is_valid:
        raise ValueError("Cannot generate image for invalid prompt")
    if submission.generation_requested:
        raise ValueError("Image generation already requested for this submission")

    submission.generation_requested = True
    await db.flush()

    # Push to image generation queue
    await push_queue(redis, image_queue_key(), {
        "submission_id": submission.id,
        "player_id": player_id,
        "prompt": submission.raw_prompt,
        "round_id": submission.round_id,
    })

    logger.info("image_generation_queued", submission_id=submission.id, player_id=player_id)
    return submission


async def set_final_submission(
    db: AsyncSession,
    redis: aioredis.Redis,
    submission_id: str,
    player_id: str,
    round_id: str,
) -> Submission:
    """
    Mark a submission as the player's final entry for this round.
    Clears any previous final submission for this player+round.
    """
    # Verify submission
    result = await db.execute(select(Submission).where(Submission.id == submission_id))
    submission = result.scalar_one_or_none()
    if not submission:
        raise ValueError("Submission not found")
    if submission.player_id != player_id:
        raise ValueError("Not your submission")
    if not submission.generation_completed:
        raise ValueError("Image not yet generated — cannot submit")
    if submission.round_id != round_id:
        raise ValueError("Submission is from a different round")

    # Clear old final submissions for this player+round
    prev_finals_result = await db.execute(
        select(Submission).where(
            Submission.player_id == player_id,
            Submission.round_id == round_id,
            Submission.is_final == True,  # noqa: E712
        )
    )
    for prev in prev_finals_result.scalars().all():
        prev.is_final = False

    # Set this as final
    submission.is_final = True
    submission.submitted_at = utcnow()

    # Update player status
    player_result = await db.execute(select(Player).where(Player.id == player_id))
    player = player_result.scalar_one_or_none()
    if player:
        player.status = PlayerStatus.SUBMITTED

    await db.flush()

    logger.info("final_submission_set", submission_id=submission_id, player_id=player_id)
    return submission


async def get_player_submissions(
    db: AsyncSession, player_id: str, round_id: str
) -> list[Submission]:
    result = await db.execute(
        select(Submission)
        .where(Submission.player_id == player_id, Submission.round_id == round_id)
        .order_by(Submission.attempt_number)
    )
    return list(result.scalars().all())
