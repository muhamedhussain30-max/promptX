from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class ValidatePromptRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=2000)


class ValidatePromptResponse(BaseModel):
    is_valid: bool
    normalized_prompt: str
    forbidden_words_detected: list[str]
    message: str


class GenerateImageRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=2000)
    attempt_number: int = Field(default=1, ge=1)


class GenerateImageResponse(BaseModel):
    submission_id: str
    status: str   # "queued" | "generating" | "completed" | "failed"
    image_url: Optional[str] = None
    message: str = "Image generation queued"


class FinalSubmitRequest(BaseModel):
    submission_id: str


class SubmissionOut(BaseModel):
    id: str
    round_id: str
    player_id: str
    attempt_number: int
    raw_prompt: str
    is_valid: bool
    image_url: Optional[str]
    is_final: bool
    generation_completed: bool

    model_config = {"from_attributes": True}
