from typing import Optional
from pydantic import BaseModel, Field
from app.models.game import GameStatus


class GameCreate(BaseModel):
    title: str = "PromptX Prelims"
    max_players: int = Field(default=70, ge=2, le=70)
    total_rounds: int = Field(default=5, ge=1, le=20)
    round_duration: int = Field(default=60, ge=10, le=600)
    max_attempts: int = Field(default=3, ge=1, le=10)


class GameOut(BaseModel):
    id: str
    title: str
    room_code: str
    status: GameStatus
    max_players: int
    total_rounds: int
    round_duration: int
    max_attempts: int
    current_round_number: int
    host_id: str

    model_config = {"from_attributes": True}


class GameSummary(BaseModel):
    id: str
    title: str
    room_code: str
    status: GameStatus
    player_count: int
    max_players: int
    current_round_number: int
    total_rounds: int

    model_config = {"from_attributes": True}


class ShortlistConfig(BaseModel):
    """Defines how many players advance from the current round."""
    method: str = Field(default="count", pattern="^(count|percent|manual)$")
    value: int = Field(default=40, ge=1)   # count or percentage


class AdvancementDecision(BaseModel):
    advancing_player_ids: list[str]
