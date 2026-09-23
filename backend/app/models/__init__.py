"""
Import all models so Alembic can discover them via Base.metadata.
"""
from app.models.user import User
from app.models.game import Game, GameStatus
from app.models.player import Player, PlayerStatus
from app.models.challenge import Challenge, Difficulty, ChallengeCategory
from app.models.round import Round, RoundStatus
from app.models.submission import Submission
from app.models.score import Score, LeaderboardEntry

__all__ = [
    "User",
    "Game",
    "GameStatus",
    "Player",
    "PlayerStatus",
    "Challenge",
    "Difficulty",
    "ChallengeCategory",
    "Round",
    "RoundStatus",
    "Submission",
    "Score",
    "LeaderboardEntry",
]
