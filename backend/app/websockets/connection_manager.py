"""
ConnectionManager — tracks all live WebSocket connections grouped by room.

Architecture:
  - Each room has a set of (player_id, WebSocket) pairs
  - The host connection is tracked separately per room
  - Supports targeted sends (to one player) and room broadcasts
  - Thread-safe via asyncio (single-threaded event loop assumption)
"""
import asyncio
import json
from typing import Optional
from fastapi import WebSocket
from app.config.logging import logger


class ConnectionManager:
    def __init__(self):
        # room_code → {player_id: WebSocket}
        self._rooms: dict[str, dict[str, WebSocket]] = {}
        # room_code → host WebSocket (also stored in _rooms as "host:{user_id}")
        self._hosts: dict[str, WebSocket] = {}
        # websocket → (room_code, player_id)  for reverse lookup on disconnect
        self._reverse: dict[int, tuple[str, str]] = {}

    # ── Connection lifecycle ───────────────────────────────────────────────────

    async def connect(
        self,
        websocket: WebSocket,
        room_code: str,
        player_id: str,
        is_host: bool = False,
    ) -> None:
        await websocket.accept()

        if room_code not in self._rooms:
            self._rooms[room_code] = {}

        self._rooms[room_code][player_id] = websocket
        self._reverse[id(websocket)] = (room_code, player_id)

        if is_host:
            self._hosts[room_code] = websocket

        logger.info(
            "ws_connected",
            room_code=room_code,
            player_id=player_id,
            is_host=is_host,
            total_in_room=len(self._rooms[room_code]),
        )

    def disconnect(self, websocket: WebSocket) -> tuple[Optional[str], Optional[str]]:
        """Remove a connection. Returns (room_code, player_id) or (None, None)."""
        ws_id = id(websocket)
        if ws_id not in self._reverse:
            return None, None

        room_code, player_id = self._reverse.pop(ws_id)

        if room_code in self._rooms:
            self._rooms[room_code].pop(player_id, None)
            if not self._rooms[room_code]:
                del self._rooms[room_code]

        if room_code in self._hosts and self._hosts[room_code] is websocket:
            del self._hosts[room_code]

        logger.info("ws_disconnected", room_code=room_code, player_id=player_id)
        return room_code, player_id

    # ── Sending helpers ────────────────────────────────────────────────────────

    def _build_message(self, event: str, data: dict) -> str:
        return json.dumps({"event": event, "data": data})

    async def send_to(self, websocket: WebSocket, event: str, data: dict) -> None:
        """Send a message to a single connection."""
        try:
            await websocket.send_text(self._build_message(event, data))
        except Exception as e:
            logger.warning("ws_send_error", error=str(e))

    async def send_to_player(self, room_code: str, player_id: str, event: str, data: dict) -> None:
        """Send a message to a specific player in a room."""
        ws = self._rooms.get(room_code, {}).get(player_id)
        if ws:
            await self.send_to(ws, event, data)

    async def broadcast(self, room_code: str, event: str, data: dict) -> None:
        """Broadcast to ALL connections in a room (players + host)."""
        connections = list(self._rooms.get(room_code, {}).values())
        if not connections:
            return
        message = self._build_message(event, data)
        results = await asyncio.gather(
            *[ws.send_text(message) for ws in connections],
            return_exceptions=True,
        )
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning("ws_broadcast_error", room_code=room_code, error=str(result))

    async def broadcast_except(
        self, room_code: str, exclude_player_id: str, event: str, data: dict
    ) -> None:
        """Broadcast to everyone in a room EXCEPT one player."""
        connections = {
            pid: ws
            for pid, ws in self._rooms.get(room_code, {}).items()
            if pid != exclude_player_id
        }
        if not connections:
            return
        message = self._build_message(event, data)
        await asyncio.gather(
            *[ws.send_text(message) for ws in connections.values()],
            return_exceptions=True,
        )

    async def send_to_host(self, room_code: str, event: str, data: dict) -> None:
        ws = self._hosts.get(room_code)
        if ws:
            await self.send_to(ws, event, data)

    # ── Introspection ──────────────────────────────────────────────────────────

    def get_connected_player_ids(self, room_code: str) -> list[str]:
        return list(self._rooms.get(room_code, {}).keys())

    def get_connection_count(self, room_code: str) -> int:
        return len(self._rooms.get(room_code, {}))

    def is_connected(self, room_code: str, player_id: str) -> bool:
        return player_id in self._rooms.get(room_code, {})


# Singleton shared across the application
manager = ConnectionManager()
