"""
Database configuration and session management.
"""
import logging
from typing import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import declarative_base

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Base class for SQLAlchemy models
Base = declarative_base()

# Global engine and session maker
_engine: AsyncEngine | None = None
_session_maker: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Get or create the global database engine."""
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.DATABASE_URL,
            echo=settings.DEBUG,  # Log SQL queries in debug mode
            pool_pre_ping=True,  # Verify connections before using
        )
        # Log at DEBUG level only to avoid exposing credentials in production logs
        logger.debug(f"Created database engine for {settings.DATABASE_URL}")
    return _engine


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    """Get or create the global session maker."""
    global _session_maker
    if _session_maker is None:
        engine = get_engine()
        _session_maker = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        logger.info("Created database session maker")
    return _session_maker


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get a database session with automatic commit on success.

    The session automatically commits on successful completion and rolls back on error.
    For explicit transaction control, pass the session as a parameter instead of 
    using this context manager in nested calls.

    Usage:
        async with get_session() as session:
            result = await session.execute(query)
            # session.commit() is called automatically on exit
    """
    session_maker = get_session_maker()
    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """
    Initialize database tables.

    Creates all tables defined in Base.metadata.
    In production, use Alembic migrations instead.
    
    Raises:
        RuntimeError: If called in production environment
    """
    from app.core.config import get_settings
    
    settings = get_settings()
    if settings.ENVIRONMENT == "production":
        raise RuntimeError(
            "Cannot use init_db() in production environment. "
            "Use Alembic migrations instead: 'alembic upgrade head'"
        )
    
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables initialized")


async def close_db() -> None:
    """Close database connections."""
    global _engine, _session_maker
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_maker = None
        logger.info("Database connections closed")
