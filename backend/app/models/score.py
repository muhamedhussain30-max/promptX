"""
Score model — stores individual scoring components for each submission.
Only one Score per player per round (for their final submission).
"""
from typing import Optional
from sqlalchemy import String, Integer, Float, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base
from app.models.base_mixin import UUIDMixin, TimestampMixin


class Score(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "scores"

    submission_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("submissions.id"), nullable=False, unique=True, index=True
    )
    round_id: Mapped[str] = mapped_column(String(36), ForeignKey("rounds.id"), nullable=False, index=True)
    player_id: Mapped[str] = mapped_column(String(36), ForeignKey("players.id"), nullable=False, index=True)

    # ── Component scores ────────────────────────────────────────────────────
    accuracy: Mapped[int] = mapped_column(Integer, default=0)       # /50
    compliance: Mapped[int] = mapped_column(Integer, default=0)     # /20
    creativity: Mapped[int] = mapped_column(Integer, default=0)     # /10
    speed: Mapped[int] = mapped_column(Integer, default=0)          # /10
    efficiency: Mapped[int] = mapped_column(Integer, default=0)     # /10
    total: Mapped[int] = mapped_column(Integer, default=0)          # /100

    # Detailed accuracy breakdown (stored as JSON for transparency)
    accuracy_breakdown: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships
    submission: Mapped["Submission"] = relationship("Submission", back_populates="score")  # noqa: F821
    round: Mapped["Round"] = relationship("Round", back_populates="scores")  # noqa: F821
    player: Mapped["Player"] = relationship("Player", back_populates="scores")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Score player={self.player_id} total={self.total}>"


class LeaderboardEntry(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "leaderboard_entries"

    game_id: Mapped[str] = mapped_column(String(36), ForeignKey("games.id"), nullable=False, index=True)
    round_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("rounds.id"), nullable=True, index=True)
    player_id: Mapped[str] = mapped_column(String(36), ForeignKey("players.id"), nullable=False, index=True)

    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    round_score: Mapped[int] = mapped_column(Integer, default=0)
    cumulative_score: Mapped[int] = mapped_column(Integer, default=0)
    is_advanced: Mapped[Optional[bool]] = mapped_column(default=None)  # None = pending

    def __repr__(self) -> str:
        return f"<LeaderboardEntry rank={self.rank} player={self.player_id}>"
