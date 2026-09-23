"""
Game and GameRoom models.
A Game is a complete contest session. Each game has one active GameRoom (identified
by its room_code) and multiple Rounds.
"""
from typing import Optional
from sqlalchemy import String, Integer, ForeignKey, Enum as SAEnum, Boolean, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base
from app.models.base_mixin import UUIDMixin, TimestampMixin
import enum


class GameStatus(str, enum.Enum):
    LOBBY = "LOBBY"
    COUNTDOWN = "COUNTDOWN"
    ROUND_ACTIVE = "ROUND_ACTIVE"
    ROUND_PROCESSING = "ROUND_PROCESSING"
    LEADERBOARD = "LEADERBOARD"
    SHORTLISTING = "SHORTLISTING"
    NEXT_ROUND = "NEXT_ROUND"
    FINISHED = "FINISHED"


class Game(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "games"

    title: Mapped[str] = mapped_column(String(200), nullable=False, default="PromptX Prelims")
    room_code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False, index=True)
    host_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    status: Mapped[GameStatus] = mapped_column(
        SAEnum(GameStatus), nullable=False, default=GameStatus.LOBBY
    )

    # Configuration
    max_players: Mapped[int] = mapped_column(Integer, default=70)
    total_rounds: Mapped[int] = mapped_column(Integer, default=5)
    round_duration: Mapped[int] = mapped_column(Integer, default=60)   # seconds
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    current_round_number: Mapped[int] = mapped_column(Integer, default=0)

    # Shortlisting config (JSON stored as string)
    advancement_config: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    # Relationships
    host: Mapped["User"] = relationship("User", back_populates="games")  # noqa: F821
    players: Mapped[list["Player"]] = relationship("Player", back_populates="game")  # noqa: F821
    rounds: Mapped[list["Round"]] = relationship("Round", back_populates="game", order_by="Round.round_number")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Game {self.room_code} [{self.status}]>"
