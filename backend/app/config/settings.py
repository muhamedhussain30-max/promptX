"""
Application settings loaded from environment variables.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ────────────────────────────────────────────────────────────────
    app_name: str = "PromptX Prelims"
    app_version: str = "1.0.0"
    debug: bool = False
    secret_key: str = "change-me-in-production-use-a-long-random-string"
    allowed_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # ── Database ───────────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://promptx:promptx@localhost:5432/promptx"
    database_url_sync: str = "postgresql+psycopg2://promptx:promptx@localhost:5432/promptx"

    # ── Redis ──────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    redis_max_connections: int = 20

    # ── AI Provider ────────────────────────────────────────────────────────
    ai_provider: Literal["mock", "openai", "huggingface", "gemini", "nanobanana", "stability", "replicate"] = "mock"
    image_generation_api_key: str = ""
    image_evaluation_api_key: str = ""
    hf_token: str = ""                   # HuggingFace user access token (hf_...)
    nanobanana_api_key: str = ""         # Nano Banana API key (nb_...)
    gemini_api_key: str = ""             # Google Gemini API key (AIza...)
    mock_generation_delay: float = 1.5   # seconds to simulate generation in mock mode

    # ── Game Defaults ──────────────────────────────────────────────────────
    max_players_per_room: int = 70
    default_round_duration: int = 600     # seconds (10 minutes)
    default_max_attempts: int = 3
    default_rounds: int = 5
    room_code_length: int = 6
    countdown_seconds: int = 5

    # ── Security ───────────────────────────────────────────────────────────
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480  # 8 hours for a game session

    # ── Logging ────────────────────────────────────────────────────────────
    log_level: str = "INFO"


settings = Settings()
