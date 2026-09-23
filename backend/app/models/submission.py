"""
Submission model — a player's attempt in a round.
Each player may have multiple Submissions (attempts) per round, but only
one is marked as final.
"""
from typing import Optional
from datetime import datetime
from sqlalchemy import String, Integer, ForeignKey, DateTime, Text, Boolean, JSON, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base
from app.models.base_mixin import UUIDMixin, TimestampMixin


class Submission(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "submissions"

    round_id: Mapped[str] = mapped_column(String(36), ForeignKey("rounds.id"), nullable=False, index=True)
    player_id: Mapped[str] = mapped_column(String(36), ForeignKey("players.id"), nullable=False, index=True)

    # Attempt number (1, 2, 3 ...)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Raw prompt as entered by player
    raw_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    # Normalized version used for validation
    normalized_prompt: Mapped[str] = mapped_column(Text, nullable=False)

    # Validation
    is_valid: Mapped[bool] = mapped_column(Boolean, default=False)
    validation_errors: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # Image — stored as URL or base64 data URI (Text to accommodate data URIs)
    image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    image_generated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Player selects this as their final submission
    is_final: Mapped[bool] = mapped_column(Boolean, default=False)

    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Processing flags
    generation_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    generation_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    evaluation_completed: Mapped[bool] = mapped_column(Boolean, default=False)

    # Time from round start to valid submission (milliseconds)
    submission_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Suspicious activity flag
    is_suspicious: Mapped[bool] = mapped_column(Boolean, default=False)
    suspicious_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Relationships
    round: Mapped["Round"] = relationship("Round", back_populates="submissions")  # noqa: F821
    player: Mapped["Player"] = relationship("Player", back_populates="submissions")  # noqa: F821
    score: Mapped[Optional["Score"]] = relationship("Score", back_populates="submission", uselist=False)  # noqa: F821

    def __repr__(self) -> str:
        return f"<Submission player={self.player_id} attempt={self.attempt_number} valid={self.is_valid}>"
