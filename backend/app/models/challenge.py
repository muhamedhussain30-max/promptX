"""
Challenge model — a target concept with forbidden words and evaluation criteria.
"""
from typing import Optional
from sqlalchemy import String, Integer, Text, Enum as SAEnum, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base
from app.models.base_mixin import UUIDMixin, TimestampMixin
import enum


class Difficulty(str, enum.Enum):
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"
    EXPERT = "EXPERT"


class ChallengeCategory(str, enum.Enum):
    ANIMALS = "Animals"
    PEOPLE = "People"
    FOOD = "Food"
    VEHICLES = "Vehicles"
    FANTASY = "Fantasy"
    ARCHITECTURE = "Architecture"
    NATURE = "Nature"
    SPORTS = "Sports"
    MOVIES = "Movies"
    OBJECTS = "Objects"
    SURREAL = "Surreal"
    TECHNOLOGY = "Technology"


class Challenge(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "challenges"

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    target_description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[ChallengeCategory] = mapped_column(
        SAEnum(ChallengeCategory), nullable=False, default=ChallengeCategory.ANIMALS
    )
    difficulty: Mapped[Difficulty] = mapped_column(
        SAEnum(Difficulty), nullable=False, default=Difficulty.MEDIUM
    )

    # Forbidden words as JSON list
    forbidden_words: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    # Evaluation criteria (hidden from players)
    required_objects: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    required_attributes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    required_scene: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    required_relationships: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    # Optional reference image URL for evaluation
    reference_image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    is_active: Mapped[bool] = mapped_column(default=True)

    # Relationships
    rounds: Mapped[list["Round"]] = relationship("Round", back_populates="challenge")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Challenge {self.title} [{self.difficulty}]>"
