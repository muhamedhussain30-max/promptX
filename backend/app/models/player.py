"""
Player model — a contestant in a game. No user account needed; identified by
session token generated at join time.
"""
from typing import Optional
from sqlalchemy import String, Integer, ForeignKey, Boolean, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base
from app.models.base_mixin import UUIDMixin, TimestampMixin
import enum


class PlayerStatus(str, enum.Enum):
    WAITING = "WAITING"     # In lobby, not ready
    READY = "READY"         # In lobby, ready
    ACTIVE = "ACTIVE"       # Playing current round
    SUBMITTED = "SUBMITTED" # Submitted this round
    ELIMINATED = "ELIMINATED"
    ADVANCED = "ADVANCED"
    WINNER = "WINNER"
    DISCONNECTED = "DISCONNECTED"


class Player(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "players"

    game_id: Mapped[str] = mapped_column(String(36), ForeignKey("games.id"), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    session_token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    status: Mapped[PlayerStatus] = mapped_column(
        SAEnum(PlayerStatus), nullable=False, default=PlayerStatus.WAITING
    )
    is_ready: Mapped[bool] = mapped_column(Boolean, default=False)
    current_round: Mapped[int] = mapped_column(Integer, default=0)
    total_score: Mapped[int] = mapped_column(Integer, default=0)
    rank: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationships
    game: Mapped["Game"] = relationship("Game", back_populates="players")  # noqa: F821
    submissions: Mapped[list["Submission"]] = relationship("Submission", back_populates="player")  # noqa: F821
    scores: Mapped[list["Score"]] = relationship("Score", back_populates="player")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Player {self.display_name} [{self.status}]>"
