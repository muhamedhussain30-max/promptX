"""
ScoringWorker — triggered after a round ends.
Iterates all final submissions, runs scoring, updates leaderboard, broadcasts results.
"""
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database.base import AsyncSessionLocal
from app.database.redis import get_redis
from app.models.submission import Submission
from app.models.player import Player, PlayerStatus
from app.models.score import Score
from app.models.round import Round
from app.models.challenge import Challenge
from app.models.game import Game, GameStatus
from app.services.round_service import complete_round
from app.services.shortlist_service import build_round_leaderboard
from app.services import transition_game_state
from app.websockets import event_emitter as emit
from app.config.logging import logger


async def process_round_scores(room_code: str, game_id: str, round_id: str) -> None:
    """
    Called as an asyncio task after a round ends.
    1. Score all final submissions.
    2. Broadcast individual scores.
    3. Build & broadcast leaderboard.
    4. Transition game to LEADERBOARD state.
    """
    async with AsyncSessionLocal() as db:
        redis = await get_redis()

        try:
            # Fetch round + challenge
            round_result = await db.execute(select(Round).where(Round.id == round_id))
            rnd = round_result.scalar_one_or_none()
            if not rnd:
                logger.error("scoring_round_not_found", round_id=round_id)
                return

            challenge_result = await db.execute(
                select(Challenge).where(Challenge.id == rnd.challenge_id)
            )
            challenge = challenge_result.scalar_one_or_none()

            # Fetch game once — reuse throughout
            game = await _get_game(db, game_id)
            if not game:
                logger.error("scoring_game_not_found", game_id=game_id)
                return

            # Fetch all final submissions for this round
            subs_result = await db.execute(
                select(Submission)
                .where(Submission.round_id == round_id, Submission.is_final == True)  # noqa: E712
            )
            submissions = list(subs_result.scalars().all())

            from app.scoring.engine import score_submission

            scored_player_ids = set()

            for submission in submissions:
                # Skip if already scored (idempotency guard)
                existing_score = await db.execute(
                    select(Score).where(Score.submission_id == submission.id)
                )
                if existing_score.scalar_one_or_none():
                    continue

                player_result = await db.execute(
                    select(Player).where(Player.id == submission.player_id)
                )
                player = player_result.scalar_one_or_none()
                if not player:
                    continue

                breakdown = await score_submission(
                    submission=submission,
                    challenge=challenge,
                    round_duration=rnd.duration,
                )

                score = Score(
                    submission_id=submission.id,
                    round_id=round_id,
                    player_id=player.id,
                    accuracy=breakdown["accuracy"],
                    compliance=breakdown["compliance"],
                    creativity=breakdown["creativity"],
                    speed=breakdown["speed"],
                    efficiency=breakdown["efficiency"],
                    total=breakdown["total"],
                    accuracy_breakdown=breakdown.get("accuracy_breakdown"),
                )
                db.add(score)
                player.total_score += breakdown["total"]
                submission.evaluation_completed = True
                scored_player_ids.add(player.id)

                await db.flush()

                await emit.emit_score(room_code, player.id, {
                    "round_id":          round_id,
                    # legacy 0-10 components
                    "accuracy":          breakdown["accuracy"],
                    "compliance":        breakdown["compliance"],
                    "creativity":        breakdown["creativity"],
                    "speed":             breakdown["speed"],
                    "efficiency":        breakdown["efficiency"],
                    "total":             breakdown["total"],
                    # new 0-100 rubric fields
                    "match_score":       breakdown.get("match_score", 0),
                    "subject_score":     breakdown.get("subject_score", 0),
                    "scene_score":       breakdown.get("scene_score", 0),
                    "composition_score": breakdown.get("composition_score", 0),
                    "concept_coverage":  breakdown.get("concept_coverage", 0),
                    "creativity_100":    breakdown.get("creativity_100", 0),
                    "speed_100":         breakdown.get("speed_100", 0),
                    "efficiency_100":    breakdown.get("efficiency_100", 0),
                    # full breakdown including per-concept results
                    "accuracy_breakdown": breakdown.get("accuracy_breakdown"),
                    # image so ResultsPage can show it
                    "image_url":         submission.image_url,
                    "raw_prompt":        submission.raw_prompt,
                })

                logger.info(
                    "submission_scored",
                    player_id=player.id,
                    total=breakdown["total"],
                    room_code=room_code,
                )

            # Complete the round
            await complete_round(db, redis, round_id, game)
            await db.commit()

            # Build and broadcast leaderboard
            leaderboard = await build_round_leaderboard(db, game_id, round_id)

            await emit.emit_leaderboard(room_code, {
                "game_id": game_id,
                "round_number": rnd.round_number,
                "total_rounds": game.total_rounds,
                "entries": leaderboard,
            })

            # Transition to LEADERBOARD
            await transition_game_state(db, redis, game_id, GameStatus.LEADERBOARD)
            await db.commit()

            logger.info("round_scoring_complete", round_id=round_id, scored=len(scored_player_ids))

        except Exception as e:
            logger.error("scoring_worker_error", round_id=round_id, error=str(e))
            # Broadcast error to all players in the room
            await emit.emit_error(room_code, "broadcast", f"Scoring error: {str(e)}")


async def _get_game(db: AsyncSession, game_id: str) -> Game | None:
    result = await db.execute(select(Game).where(Game.id == game_id))
    return result.scalar_one_or_none()
