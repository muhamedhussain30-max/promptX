"""
TimerService — server-side authoritative round countdown.
Runs as a background asyncio task; broadcasts ticks via the WebSocket manager.
"""
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Callable, Awaitable, Optional

from app.config.logging import logger


class RoundTimer:
    """
    Manages a single round's countdown.
    Calls `on_tick` every second with remaining_seconds.
    Calls `on_expire` when the timer reaches zero.
    """

    def __init__(
        self,
        room_code: str,
        round_number: int,
        duration: int,
        on_tick: Callable[[str, int, float], Awaitable[None]],
        on_expire: Callable[[str, int], Awaitable[None]],
    ):
        self.room_code = room_code
        self.round_number = round_number
        self.duration = duration
        self.on_tick = on_tick
        self.on_expire = on_expire
        self._task: Optional[asyncio.Task] = None
        self._end_time: Optional[datetime] = None
        self._cancelled = False

    def start(self) -> None:
        self._end_time = datetime.now(timezone.utc) + timedelta(seconds=self.duration)
        self._task = asyncio.create_task(self._run())

    def cancel(self) -> None:
        self._cancelled = True
        if self._task:
            self._task.cancel()

    async def _run(self) -> None:
        try:
            while True:
                now = datetime.now(timezone.utc)
                remaining = (self._end_time - now).total_seconds()

                if remaining <= 0:
                    await self.on_expire(self.room_code, self.round_number)
                    break

                await self.on_tick(self.room_code, self.round_number, remaining)
                await asyncio.sleep(1.0)

        except asyncio.CancelledError:
            logger.info("timer_cancelled", room_code=self.room_code, round_number=self.round_number)
        except Exception as e:
            logger.error("timer_error", room_code=self.room_code, error=str(e))


# Registry of active timers per room
_active_timers: dict[str, RoundTimer] = {}


def register_timer(room_code: str, timer: RoundTimer) -> None:
    # Cancel any existing timer for this room
    if room_code in _active_timers:
        _active_timers[room_code].cancel()
    _active_timers[room_code] = timer
    timer.start()


def cancel_timer(room_code: str) -> None:
    if room_code in _active_timers:
        _active_timers[room_code].cancel()
        del _active_timers[room_code]


def get_timer(room_code: str) -> Optional[RoundTimer]:
    return _active_timers.get(room_code)
