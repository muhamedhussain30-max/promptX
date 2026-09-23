"""
SQLAlchemy async engine and session factory.
Supports both PostgreSQL (production) and SQLite (local dev).
"""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from app.config.settings import settings

# SQLite needs check_same_thread=False and no pool settings
_is_sqlite = settings.database_url.startswith("sqlite")

_connect_args = {"check_same_thread": False} if _is_sqlite else {}
_pool_kwargs = {} if _is_sqlite else {"pool_size": 10, "max_overflow": 20}

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=not _is_sqlite,
    connect_args=_connect_args,
    **_pool_kwargs,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


async def get_db() -> AsyncSession:
    """FastAPI dependency that yields an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_all_tables() -> None:
    """Create all tables (used for SQLite local dev instead of Alembic)."""
    # Import all models so metadata is populated
    import app.models  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
