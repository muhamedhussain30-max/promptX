"""
FastAPI dependencies — authentication, database sessions, Redis, player/host verification.
"""
from typing import Optional
from fastapi import Depends, HTTPException, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from app.database.base import get_db
from app.database.redis import get_redis
from app.models.user import User
from app.models.player import Player
from app.services.auth_service import decode_token, get_user_by_username
from sqlalchemy import select


# ── JWT host auth ──────────────────────────────────────────────────────────────

async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Decode JWT and return the authenticated User (host only)."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header",
        )
    token = authorization.removeprefix("Bearer ").strip()
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    username = payload.get("sub")
    user = await get_user_by_username(db, username)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


async def get_current_host(user: User = Depends(get_current_user)) -> User:
    if not user.is_host:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Host role required")
    return user


# ── Player session auth ────────────────────────────────────────────────────────

async def get_current_player(
    x_player_token: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
) -> Player:
    """Validate X-Player-Token header and return the Player."""
    if not x_player_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Player-Token header required",
        )
    result = await db.execute(select(Player).where(Player.session_token == x_player_token))
    player = result.scalar_one_or_none()
    if not player:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid player token")
    return player


# ── Re-export commonly used deps ───────────────────────────────────────────────

async def get_redis_dep() -> aioredis.Redis:
    return await get_redis()
