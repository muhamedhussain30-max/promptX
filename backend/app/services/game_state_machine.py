"""
Explicit game state machine.

Valid transitions:
  LOBBY           → COUNTDOWN
  COUNTDOWN       → ROUND_ACTIVE
  ROUND_ACTIVE    → ROUND_PROCESSING
  ROUND_PROCESSING→ LEADERBOARD
  LEADERBOARD     → SHORTLISTING  (if more rounds remain and elimination configured)
  LEADERBOARD     → NEXT_ROUND    (auto-advance when no shortlisting needed)
  LEADERBOARD     → FINISHED      (final round complete)
  SHORTLISTING    → NEXT_ROUND
  NEXT_ROUND      → COUNTDOWN
  * any           → FINISHED      (host force-ends)
"""
from app.models.game import GameStatus
from app.config.logging import logger

# Allowed (from → {to, ...}) transitions
_TRANSITIONS: dict[GameStatus, set[GameStatus]] = {
    GameStatus.LOBBY:             {GameStatus.COUNTDOWN, GameStatus.FINISHED},
    GameStatus.COUNTDOWN:         {GameStatus.ROUND_ACTIVE, GameStatus.FINISHED},
    GameStatus.ROUND_ACTIVE:      {GameStatus.ROUND_PROCESSING, GameStatus.FINISHED},
    GameStatus.ROUND_PROCESSING:  {GameStatus.LEADERBOARD, GameStatus.FINISHED},
    GameStatus.LEADERBOARD:       {GameStatus.SHORTLISTING, GameStatus.NEXT_ROUND, GameStatus.FINISHED},
    GameStatus.SHORTLISTING:      {GameStatus.NEXT_ROUND, GameStatus.FINISHED},
    GameStatus.NEXT_ROUND:        {GameStatus.COUNTDOWN, GameStatus.FINISHED},
    GameStatus.FINISHED:          set(),  # terminal
}


class InvalidStateTransitionError(Exception):
    def __init__(self, from_state: GameStatus, to_state: GameStatus):
        super().__init__(f"Cannot transition from {from_state} → {to_state}")
        self.from_state = from_state
        self.to_state = to_state


def assert_transition(current: GameStatus, desired: GameStatus) -> None:
    """Raise if the transition is not allowed."""
    allowed = _TRANSITIONS.get(current, set())
    if desired not in allowed:
        raise InvalidStateTransitionError(current, desired)


def can_transition(current: GameStatus, desired: GameStatus) -> bool:
    return desired in _TRANSITIONS.get(current, set())


def can_submit_prompt(status: GameStatus) -> bool:
    """Players may only submit during an active round."""
    return status == GameStatus.ROUND_ACTIVE


def can_join(status: GameStatus) -> bool:
    """Players may only join while in the lobby."""
    return status == GameStatus.LOBBY


def log_transition(game_id: str, from_state: GameStatus, to_state: GameStatus) -> None:
    logger.info(
        "game_state_transition",
        game_id=game_id,
        from_state=from_state.value,
        to_state=to_state.value,
    )
