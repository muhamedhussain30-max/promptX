"""
Canonical WebSocket event type definitions.
All server→client and client→server messages use these string constants.
"""
from enum import Enum


class ServerEvent(str, Enum):
    """Events the server broadcasts to clients."""
    # Connection lifecycle
    CONNECTED = "connected"
    ERROR = "error"

    # Lobby
    PLAYER_JOINED = "player_joined"
    PLAYER_LEFT = "player_left"
    PLAYER_READY = "player_ready"
    PLAYER_UNREADY = "player_unready"
    LOBBY_STATE = "lobby_state"

    # Game flow
    GAME_STARTED = "game_started"
    COUNTDOWN_STARTED = "countdown_started"
    COUNTDOWN_TICK = "countdown_tick"
    ROUND_STARTED = "round_started"
    TIMER_UPDATED = "timer_updated"
    ROUND_ENDED = "round_ended"
    ROUND_PROCESSING = "round_processing"

    # Submissions & generation
    PROMPT_VALIDATED = "prompt_validated"
    IMAGE_GENERATION_STARTED = "image_generation_started"
    IMAGE_GENERATED = "image_generated"
    SUBMISSION_COMPLETED = "submission_completed"

    # Scoring & leaderboard
    SCORE_CALCULATED = "score_calculated"
    LEADERBOARD_UPDATED = "leaderboard_updated"

    # Advancement
    PLAYER_ADVANCED = "player_advanced"
    PLAYER_ELIMINATED = "player_eliminated"
    SHORTLIST_ANNOUNCED = "shortlist_announced"

    # Next round / finish
    NEXT_ROUND_STARTED = "next_round_started"
    GAME_FINISHED = "game_finished"
    WINNER_ANNOUNCED = "winner_announced"

    # Host controls
    GAME_PAUSED = "game_paused"
    GAME_RESUMED = "game_resumed"
    PLAYER_REMOVED = "player_removed"


class ClientEvent(str, Enum):
    """Events the client sends to the server."""
    PING = "ping"
    READY_TOGGLE = "ready_toggle"
    SUBMIT_PROMPT = "submit_prompt"         # validate + queue generation
    SELECT_SUBMISSION = "select_submission" # mark a submission as final
    HOST_START_GAME = "host_start_game"
    HOST_START_ROUND = "host_start_round"
    HOST_END_ROUND = "host_end_round"
    HOST_PAUSE = "host_pause"
    HOST_RESUME = "host_resume"
    HOST_SHORTLIST = "host_shortlist"
    HOST_NEXT_ROUND = "host_next_round"
    HOST_END_GAME = "host_end_game"
    HOST_REMOVE_PLAYER = "host_remove_player"
