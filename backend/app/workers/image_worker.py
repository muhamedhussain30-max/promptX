"""
ImageGenerationWorker — processes jobs from the Redis image queue.

Architecture:
  - Runs as an asyncio background task launched at app startup
  - Processes one job at a time (sequential per room, concurrent across rooms)
  - On completion: updates the Submission record and notifies the player via WebSocket
  - Falls back gracefully on generation failure
"""
import asyncio
from datetime import datetime
from sqlalchemy import select

from app.database.base import AsyncSessionLocal
from app.database.redis import get_redis, pop_queue, image_queue_key
from app.models.submission import Submission
from app.models.round import Round, RoundStatus
from app.models.game import Game
from app.services.image_gen.factory import get_image_generation_provider
from app.websockets import event_emitter as emit
from app.config.logging import logger


_WORKER_RUNNING = False


async def image_generation_worker() -> None:
    """
    Long-running background task.
    Pop jobs from the queue and process them sequentially.
    """
    global _WORKER_RUNNING
    _WORKER_RUNNING = True
    logger.info("image_worker_started")

    provider = get_image_generation_provider()

    while _WORKER_RUNNING:
        try:
            redis = await get_redis()
            job = await pop_queue(redis, image_queue_key(), timeout=5)

            if job is None:
                continue  # timeout, loop again

            await _process_job(job, provider)

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("image_worker_loop_error", error=str(e))
            await asyncio.sleep(1.0)

    logger.info("image_worker_stopped")


async def _process_job(job: dict, provider) -> None:
    """Process a single image-generation job."""
    submission_id = job.get("submission_id")
    player_id = job.get("player_id")
    prompt = job.get("prompt", "")

    logger.info("image_generation_processing", submission_id=submission_id, player_id=player_id)

    async with AsyncSessionLocal() as db:
        # Fetch submission + validate it's still relevant
        result = await db.execute(select(Submission).where(Submission.id == submission_id))
        submission = result.scalar_one_or_none()

        if not submission:
            logger.warning("image_job_submission_not_found", submission_id=submission_id)
            return

        # Fetch the game's room_code for WebSocket notification
        round_result = await db.execute(select(Round).where(Round.id == submission.round_id))
        rnd = round_result.scalar_one_or_none()

        room_code: str = ""
        if rnd:
            game_result = await db.execute(select(Game).where(Game.id == rnd.game_id))
            game = game_result.scalar_one_or_none()
            if game:
                room_code = game.room_code

                # If round expired, still generate (rule: valid submissions already accepted)
                # but don't block scoring
                if rnd.status not in (RoundStatus.ACTIVE, RoundStatus.PROCESSING):
                    logger.info(
                        "image_gen_round_already_closed",
                        round_id=rnd.id,
                        status=rnd.status,
                    )

        # Notify player generation started
        if room_code:
            await emit.emit_image_generation_started(room_code, player_id, submission_id)

        # Generate
        gen_result = await provider.generate(prompt)

        if gen_result.success and gen_result.image_url:
            submission.image_url = gen_result.image_url
            submission.generation_completed = True
            submission.image_generated_at = datetime.utcnow()  # naive UTC for SQLite
            await db.commit()

            logger.info(
                "image_generation_success",
                submission_id=submission_id,
                image_url=gen_result.image_url,
            )

            if room_code:
                await emit.emit_image_generated(
                    room_code,
                    player_id,
                    submission_id,
                    gen_result.image_url,
                    submission.attempt_number,
                )
        else:
            logger.error(
                "image_generation_failed",
                submission_id=submission_id,
                error=gen_result.error_message,
            )
            await db.commit()

            if room_code:
                await emit.emit_error(
                    room_code,
                    player_id,
                    f"Image generation failed: {gen_result.error_message}",
                    "GENERATION_FAILED",
                )


def start_image_worker() -> asyncio.Task:
    """Launch the image worker as an asyncio background task."""
    return asyncio.create_task(image_generation_worker())


def stop_image_worker() -> None:
    global _WORKER_RUNNING
    _WORKER_RUNNING = False
