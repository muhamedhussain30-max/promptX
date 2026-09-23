"""
PromptX Prelims — FastAPI Application Entry Point
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings, configure_logging, logger
from app.database import get_redis, close_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    configure_logging()
    logger.info("promptx_starting", version=settings.app_version, provider=settings.ai_provider)

    # Auto-create tables for SQLite local dev
    if settings.database_url.startswith("sqlite"):
        from app.database.base import create_all_tables
        await create_all_tables()
        logger.info("sqlite_tables_created")

    # Init Redis / fakeredis
    redis = await get_redis()
    try:
        await redis.ping()
        logger.info("redis_ready")
    except Exception:
        logger.info("redis_ready_fakeredis")

    # Seed challenges on first run
    try:
        from app.database.base import AsyncSessionLocal
        from app.challenges.seeder import seed_challenges
        async with AsyncSessionLocal() as db:
            count = await seed_challenges(db)
            await db.commit()
        if count:
            logger.info("challenges_seeded_on_startup", count=count)
    except Exception as e:
        logger.warning("seed_failed", error=str(e))

    # Start background image generation worker
    from app.workers.image_worker import start_image_worker, stop_image_worker
    worker_task = start_image_worker()
    logger.info("image_worker_started")

    yield

    # Cleanup
    stop_image_worker()
    worker_task.cancel()
    await close_redis()
    logger.info("promptx_stopped")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# ── CORS ───────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────────────
from app.api import games, players, rounds, auth, challenges  # noqa: E402
from app.websockets.router import router as ws_router          # noqa: E402

app.include_router(auth.router,       prefix="/api/auth",       tags=["auth"])
app.include_router(games.router,      prefix="/api/games",      tags=["games"])
app.include_router(players.router,    prefix="/api/players",    tags=["players"])
app.include_router(rounds.router,     prefix="/api/rounds",     tags=["rounds"])
app.include_router(challenges.router, prefix="/api/challenges", tags=["challenges"])
app.include_router(ws_router,         tags=["websocket"])


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": settings.app_version, "provider": settings.ai_provider}
