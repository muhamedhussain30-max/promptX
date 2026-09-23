from typing import Optional
from pydantic import BaseModel, Field
from app.models.player import PlayerStatus


class PlayerJoin(BaseModel):
    room_code: str = Field(min_length=4, max_length=10)
    display_name: str = Field(min_length=1, max_length=100)


class PlayerJoinResponse(BaseModel):
    player_id: str
    session_token: str
    game_id: str
    room_code: str
    display_name: str


class PlayerOut(BaseModel):
    id: str
    display_name: str
    status: PlayerStatus
    is_ready: bool
    total_score: int
    rank: Optional[int]

    model_config = {"from_attributes": True}


class PlayerReadyToggle(BaseModel):
    is_ready: bool
