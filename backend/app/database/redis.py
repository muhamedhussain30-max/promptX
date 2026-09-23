"""
Redis connection — uses fakeredis for local dev (REDIS_URL=fakeredis://)
or a real Redis server in production.
"""
import json
from typing import Any, Optional
from app.config.settings import settings
from app.config.logging import logger


_redis_client = None


async def get_redis():
    """Return a shared Redis/fakeredis connection."""
    global _redis_client
    if _redis_client is None:
        if settings.redis_url.startswith("fakeredis"):
            import fakeredis.aioredis as fakeredis
            _redis_client = fakeredis.FakeRedis(decode_responses=True)
            logger.info("redis_using_fakeredis")
        else:
            import redis.asyncio as aioredis
            _redis_client = aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=settings.redis_max_connections,
            )
            logger.info("redis_connected", url=settings.redis_url)
    return _redis_client


async def close_redis() -> None:
    global _redis_client
    if _redis_client is not None:
        try:
            await _redis_client.aclose()
        except Exception:
            pass
        _redis_client = None


# ── Namespaced key helpers ─────────────────────────────────────────────────────

def room_key(room_code: str) -> str:
    return f"promptx:room:{room_code}"

def room_players_key(room_code: str) -> str:
    return f"promptx:room:{room_code}:players"

def room_state_key(room_code: str) -> str:
    return f"promptx:room:{room_code}:state"

def round_key(room_code: str, round_number: int) -> str:
    return f"promptx:room:{room_code}:round:{round_number}"

def player_session_key(player_id: str) -> str:
    return f"promptx:player:{player_id}:session"

def submission_queue_key() -> str:
    return "promptx:queue:submissions"

def image_queue_key() -> str:
    return "promptx:queue:images"

def eval_queue_key() -> str:
    return "promptx:queue:evals"

def leaderboard_key(room_code: str) -> str:
    return f"promptx:room:{room_code}:leaderboard"


# ── Generic helpers ────────────────────────────────────────────────────────────

async def set_json(redis, key: str, value: Any, ttl: int = 3600) -> None:
    await redis.set(key, json.dumps(value), ex=ttl)

async def get_json(redis, key: str) -> Optional[Any]:
    raw = await redis.get(key)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None

async def delete_key(redis, key: str) -> None:
    await redis.delete(key)

async def push_queue(redis, queue_key: str, payload: Any) -> None:
    await redis.rpush(queue_key, json.dumps(payload))

async def pop_queue(redis, queue_key: str, timeout: int = 5) -> Optional[Any]:
    result = await redis.blpop(queue_key, timeout=timeout)
    if result is None:
        return None
    _, raw = result
    return json.loads(raw)
