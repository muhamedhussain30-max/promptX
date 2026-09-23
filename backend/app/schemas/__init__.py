from app.schemas.common import APIResponse, PaginatedResponse
from app.schemas.auth import UserRegister, UserLogin, TokenResponse, UserOut
from app.schemas.game import GameCreate, GameOut, GameSummary, ShortlistConfig, AdvancementDecision
from app.schemas.player import PlayerJoin, PlayerJoinResponse, PlayerOut, PlayerReadyToggle
from app.schemas.submission import (
    ValidatePromptRequest, ValidatePromptResponse,
    GenerateImageRequest, GenerateImageResponse,
    FinalSubmitRequest, SubmissionOut,
)
from app.schemas.score import ScoreBreakdown, LeaderboardEntryOut, LeaderboardOut
