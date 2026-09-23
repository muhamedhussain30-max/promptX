"""
EventEmitter — high-level helpers that build and broadcast well-typed events.
All outgoing payloads are defined here so the rest of the codebase stays clean.
"""
from typing import Optional
from app.websockets.connection_manager import manager
from app.websockets.events import ServerEvent


# ── Lobby ──────────────────────────────────────────────────────────────────────

async def emit_lobby_state(room_code: str, lobby_data: dict) -> None:
    await manager.broadcast(room_code, ServerEvent.LOBBY_STATE, lobby_data)


async def emit_player_joined(room_code: str, player: dict) -> None:
    await manager.broadcast(room_code, ServerEvent.PLAYER_JOINED, {"player": player})


async def emit_player_left(room_code: str, player_id: str, display_name: str) -> None:
    await manager.broadcast(room_code, ServerEvent.PLAYER_LEFT, {
        "player_id": player_id,
        "display_name": display_name,
    })


async def emit_player_ready(room_code: str, player_id: str, is_ready: bool) -> None:
    event = ServerEvent.PLAYER_READY if is_ready else ServerEvent.PLAYER_UNREADY
    await manager.broadcast(room_code, event, {"player_id": player_id, "is_ready": is_ready})


# ── Game flow ──────────────────────────────────────────────────────────────────

async def emit_game_started(room_code: str, game_data: dict) -> None:
    await manager.broadcast(room_code, ServerEvent.GAME_STARTED, game_data)


async def emit_countdown(room_code: str, remaining: int) -> None:
    await manager.broadcast(room_code, ServerEvent.COUNTDOWN_TICK, {"remaining": remaining})


async def emit_round_started(room_code: str, round_data: dict) -> None:
    """
    round_data must include:
      round_number, total_rounds, ends_at (ISO string), duration,
      challenge: {target_description, forbidden_words, difficulty, category}
    Note: required_objects / evaluation criteria are NOT included.
    """
    await manager.broadcast(room_code, ServerEvent.ROUND_STARTED, round_data)


async def emit_timer_tick(room_code: str, remaining_seconds: float) -> None:
    await manager.broadcast(room_code, ServerEvent.TIMER_UPDATED, {
        "remaining_seconds": round(remaining_seconds, 1),
    })


async def emit_round_ended(room_code: str, round_number: int) -> None:
    await manager.broadcast(room_code, ServerEvent.ROUND_ENDED, {
        "round_number": round_number,
        "message": "Round over! Calculating scores...",
    })


async def emit_round_processing(room_code: str) -> None:
    await manager.broadcast(room_code, ServerEvent.ROUND_PROCESSING, {
        "message": "Processing submissions...",
    })


# ── Submission & generation ────────────────────────────────────────────────────

async def emit_prompt_validated(
    room_code: str,
    player_id: str,
    is_valid: bool,
    forbidden_detected: list[str],
    message: str,
) -> None:
    await manager.send_to_player(room_code, player_id, ServerEvent.PROMPT_VALIDATED, {
        "is_valid": is_valid,
        "forbidden_words_detected": forbidden_detected,
        "message": message,
    })


async def emit_image_generation_started(room_code: str, player_id: str, submission_id: str) -> None:
    await manager.send_to_player(room_code, player_id, ServerEvent.IMAGE_GENERATION_STARTED, {
        "submission_id": submission_id,
        "message": "Generating your image...",
    })


async def emit_image_generated(
    room_code: str,
    player_id: str,
    submission_id: str,
    image_url: str,
    attempt_number: int,
) -> None:
    await manager.send_to_player(room_code, player_id, ServerEvent.IMAGE_GENERATED, {
        "submission_id": submission_id,
        "image_url": image_url,
        "attempt_number": attempt_number,
    })


async def emit_submission_completed(
    room_code: str,
    player_id: str,
    submission_id: str,
) -> None:
    await manager.send_to_player(room_code, player_id, ServerEvent.SUBMISSION_COMPLETED, {
        "submission_id": submission_id,
        "message": "Submission received!",
    })


# ── Scoring & leaderboard ──────────────────────────────────────────────────────

async def emit_score(room_code: str, player_id: str, score_data: dict) -> None:
    """Send private score breakdown to one player."""
    await manager.send_to_player(room_code, player_id, ServerEvent.SCORE_CALCULATED, score_data)


async def emit_leaderboard(room_code: str, leaderboard_data: dict) -> None:
    """Broadcast public leaderboard to all players."""
    await manager.broadcast(room_code, ServerEvent.LEADERBOARD_UPDATED, leaderboard_data)


# ── Advancement ────────────────────────────────────────────────────────────────

async def emit_shortlist(room_code: str, shortlist_data: dict) -> None:
    await manager.broadcast(room_code, ServerEvent.SHORTLIST_ANNOUNCED, shortlist_data)


async def emit_player_advanced(room_code: str, player_id: str, display_name: str) -> None:
    await manager.broadcast(room_code, ServerEvent.PLAYER_ADVANCED, {
        "player_id": player_id,
        "display_name": display_name,
    })


async def emit_player_eliminated(room_code: str, player_id: str, display_name: str) -> None:
    await manager.broadcast(room_code, ServerEvent.PLAYER_ELIMINATED, {
        "player_id": player_id,
        "display_name": display_name,
    })


# ── Next round / finish ────────────────────────────────────────────────────────

async def emit_next_round(room_code: str, next_round_number: int) -> None:
    await manager.broadcast(room_code, ServerEvent.NEXT_ROUND_STARTED, {
        "next_round_number": next_round_number,
        "message": f"Get ready for Round {next_round_number}!",
    })


async def emit_game_finished(room_code: str) -> None:
    await manager.broadcast(room_code, ServerEvent.GAME_FINISHED, {
        "message": "The contest is over!",
    })


async def emit_winner_announced(room_code: str, winners: list[dict]) -> None:
    await manager.broadcast(room_code, ServerEvent.WINNER_ANNOUNCED, {"winners": winners})


# ── Host-only ──────────────────────────────────────────────────────────────────

async def emit_player_removed(room_code: str, player_id: str, reason: str = "Removed by host") -> None:
    await manager.send_to_player(room_code, player_id, ServerEvent.PLAYER_REMOVED, {
        "reason": reason,
    })
    await manager.broadcast_except(room_code, player_id, ServerEvent.PLAYER_LEFT, {
        "player_id": player_id,
        "reason": reason,
    })


async def emit_error(room_code: str, player_id: str, message: str, code: str = "ERROR") -> None:
    await manager.send_to_player(room_code, player_id, ServerEvent.ERROR, {
        "code": code,
        "message": message,
    })
