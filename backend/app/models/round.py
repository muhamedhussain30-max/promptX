"""
Round model — one timed challenge within a Game.
"""
from typing import Optional
from datetime import datetime
from sqlalchemy import String, Integer, ForeignKey, DateTime, Enum as SAEnum, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base
from app.models.base_mixin import UUIDMixin, TimestampMixin
import enum


class RoundStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"


class Round(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "rounds"

    game_id: Mapped[str] = mapped_column(String(36), ForeignKey("games.id"), nullable=False, index=True)
    challenge_id: Mapped[str] = mapped_column(String(36), ForeignKey("challenges.id"), nullable=False)
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[RoundStatus] = mapped_column(
        SAEnum(RoundStatus), nullable=False, default=RoundStatus.PENDING
    )
    duration: Mapped[int] = mapped_column(Integer, nullable=False, default=60)  # seconds

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Number of players who participated
    participant_count: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    game: Mapped["Game"] = relationship("Game", back_populates="rounds")  # noqa: F821
    challenge: Mapped["Challenge"] = relationship("Challenge", back_populates="rounds")  # noqa: F821
    submissions: Mapped[list["Submission"]] = relationship("Submission", back_populates="round")  # noqa: F821
    scores: Mapped[list["Score"]] = relationship("Score", back_populates="round")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Round {self.round_number} [{self.status}]>"
