"""
WebSocket endpoint router.

Connection URL:
  ws://<host>/ws/{room_code}?token=<session_token>&is_host=<0|1>

- Regular players authenticate with their session_token (issued at join).
- Hosts authenticate with a JWT (issued at login) plus is_host=1.
"""
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.base import get_db, AsyncSessionLocal
from app.database.redis import get_redis
from app.websockets.connection_manager import manager
from app.websockets.events import ClientEvent, ServerEvent
from app.websockets.handlers import HANDLERS, build_lobby_payload
from app.websockets import event_emitter as emit
from app.services import get_player_by_token, get_game_by_code, decode_token
from app.models.game import GameStatus
from app.config.logging import logger

router = APIRouter()


@router.websocket("/ws/{room_code}")
async def websocket_endpoint(
    websocket: WebSocket,
    room_code: str,
    token: str = Query(..., description="Player session token OR host JWT"),
    is_host: int = Query(default=0),
    db: AsyncSession = Depends(get_db),
):
    redis = await get_redis()
    room_code = room_code.upper()
    host_flag = bool(is_host)

    # ── Authenticate ───────────────────────────────────────────────────────────
    player_id: str | None = None
    display_name: str = "Unknown"

    if host_flag:
        payload = decode_token(token)
        if payload is None:
            await websocket.close(code=4001, reason="Invalid host token")
            return
        player_id = f"host:{payload.get('sub')}"
        display_name = payload.get("display_name", "Host")
    else:
        player = await get_player_by_token(db, token)
        if player is None:
            await websocket.close(code=4001, reason="Invalid player token")
            return
        game_check = await get_game_by_code(db, room_code)
        if not game_check or player.game_id != game_check.id:
            await websocket.close(code=4003, reason="Player not in this room")
            return
        player_id = player.id
        display_name = player.display_name

    # ── Connect ────────────────────────────────────────────────────────────────
    await manager.connect(websocket, room_code, player_id, is_host=host_flag)

    # Always use a fresh DB session for the initial lobby snapshot
    # so we never serve stale ORM-cached data
    async with AsyncSessionLocal() as fresh_db:
        fresh_game = await get_game_by_code(fresh_db, room_code)
        if fresh_game:
            lobby = await build_lobby_payload(fresh_db, fresh_game)
            if fresh_game.status == GameStatus.LOBBY:
                # In lobby: broadcast to everyone so all tabs see the current player list
                await emit.emit_lobby_state(room_code, lobby)
            else:
                # Mid-game: only send state snapshot to the connecting client
                # Don't overwrite other clients' active round state
                await manager.send_to(websocket, ServerEvent.LOBBY_STATE, lobby)

    logger.info("ws_session_started", room_code=room_code, player_id=player_id, is_host=host_flag)

    # ── Message loop ───────────────────────────────────────────────────────────
    try:
        while True:
            raw = await websocket.receive_text()

            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                await emit.emit_error(room_code, player_id, "Invalid JSON", "PARSE_ERROR")
                continue

            event_name = message.get("event", "")
            payload = message.get("data", {})

            try:
                event = ClientEvent(event_name)
            except ValueError:
                await emit.emit_error(room_code, player_id, f"Unknown event: {event_name}", "UNKNOWN_EVENT")
                continue

            handler = HANDLERS.get(event)
            if handler:
                try:
                    redis_conn = await get_redis()
                    await handler(
                        ws=websocket,
                        room_code=room_code,
                        player_id=player_id,
                        payload=payload,
                        db=db,
                        redis=redis_conn,
                        is_host=host_flag,
                    )
                except Exception as e:
                    logger.error("ws_handler_error", evt=event_name, error=str(e))
                    await emit.emit_error(room_code, player_id, f"Error: {str(e)}")

    except WebSocketDisconnect:
        room, pid = manager.disconnect(websocket)
        if room and pid:
            await emit.emit_player_left(room, pid, display_name)
            logger.info("ws_player_disconnected", room_code=room, player_id=pid)
    except Exception as e:
        logger.error("ws_unexpected_error", room_code=room_code, error=str(e))
        manager.disconnect(websocket)
