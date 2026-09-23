"""
ShortlistService — determines which players advance to the next round.
Tie-breaking is fully deterministic (no random elements).
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import redis.asyncio as aioredis

from app.models.player import Player, PlayerStatus
from app.models.score import Score, LeaderboardEntry
from app.models.round import Round
from app.models.submission import Submission
from app.services.room_service import eliminate_player, advance_player
from app.config.logging import logger


def _sort_key(entry: dict) -> tuple:
    """
    Deterministic tie-breaking:
    1. Total cumulative score (desc)
    2. Accuracy this round (desc)
    3. Fastest valid submission — lowest submission_time_ms (asc, so negate)
    4. Efficiency this round (desc)
    """
    return (
        -entry["cumulative_score"],
        -entry["accuracy"],
        entry["submission_time_ms"] if entry["submission_time_ms"] is not None else 99_999_999,
        -entry["efficiency"],
    )


async def build_round_leaderboard(
    db: AsyncSession,
    game_id: str,
    round_id: str,
) -> list[dict]:
    """
    Build ranked leaderboard for a completed round.
    Returns list of dicts sorted by deterministic tie-breaking.
    """
    # Join Score + Submission + Player for this round
    result = await db.execute(
        select(Score, Player, Submission)
        .join(Player, Score.player_id == Player.id)
        .join(Submission, Score.submission_id == Submission.id)
        .where(Score.round_id == round_id, Player.game_id == game_id)
    )
    rows = result.all()

    entries = []
    for score, player, submission in rows:
        entries.append({
            "player_id": player.id,
            "display_name": player.display_name,
            "round_score": score.total,
            "cumulative_score": player.total_score,
            "accuracy": score.accuracy,
            "compliance": score.compliance,
            "creativity": score.creativity,
            "speed": score.speed,
            "efficiency": score.efficiency,
            "submission_time_ms": submission.submission_time_ms,
            "is_advanced": None,
        })

    # Include players who did NOT submit (score = 0)
    all_players_result = await db.execute(
        select(Player).where(
            Player.game_id == game_id,
            Player.status != PlayerStatus.ELIMINATED,
        )
    )
    submitted_ids = {e["player_id"] for e in entries}
    for player in all_players_result.scalars().all():
        if player.id not in submitted_ids:
            entries.append({
                "player_id": player.id,
                "display_name": player.display_name,
                "round_score": 0,
                "cumulative_score": player.total_score,
                "accuracy": 0,
                "compliance": 0,
                "creativity": 0,
                "speed": 0,
                "efficiency": 0,
                "submission_time_ms": None,
                "is_advanced": None,
            })

    entries.sort(key=_sort_key)
    for i, e in enumerate(entries):
        e["rank"] = i + 1

    return entries


async def apply_shortlist(
    db: AsyncSession,
    redis: aioredis.Redis,
    game_id: str,
    round_id: str,
    advancing_count: int,
    leaderboard: Optional[list[dict]] = None,
) -> dict[str, list[dict]]:
    """
    Advance top N players, eliminate the rest.
    Returns {"advanced": [...], "eliminated": [...]}
    """
    if leaderboard is None:
        leaderboard = await build_round_leaderboard(db, game_id, round_id)

    advanced = leaderboard[:advancing_count]
    eliminated = leaderboard[advancing_count:]

    advancing_ids = {e["player_id"] for e in advanced}
    eliminating_ids = {e["player_id"] for e in eliminated}

    for entry in advanced:
        entry["is_advanced"] = True
        await advance_player(db, redis, entry["player_id"])

    for entry in eliminated:
        entry["is_advanced"] = False
        await eliminate_player(db, redis, entry["player_id"])

    # Persist leaderboard entries
    for entry in leaderboard:
        lb = LeaderboardEntry(
            game_id=game_id,
            round_id=round_id,
            player_id=entry["player_id"],
            rank=entry["rank"],
            round_score=entry["round_score"],
            cumulative_score=entry["cumulative_score"],
            is_advanced=entry["is_advanced"],
        )
        db.add(lb)

    await db.flush()

    logger.info(
        "shortlist_applied",
        game_id=game_id,
        advancing=len(advanced),
        eliminated=len(eliminated),
    )
    return {"advanced": advanced, "eliminated": eliminated}
