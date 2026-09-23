"""
User model — represents authenticated hosts/admins.
Regular contestants use the Player model (session-based, no account required).
"""
from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base
from app.models.base_mixin import UUIDMixin, TimestampMixin


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_host: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    games: Mapped[list["Game"]] = relationship("Game", back_populates="host")  # noqa: F821

    def __repr__(self) -> str:
        return f"<User {self.username}>"
