"""Asynchronous database connection engine and session factory configuration."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

# Create async engine
engine = create_async_engine(settings.database_url, pool_pre_ping=True)

# Create session factory
async_session_maker = async_sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for obtaining database sessions in FastAPI route handlers.

    Yields:
        An active AsyncSession context.
    """
    async with async_session_maker() as session:
        yield session
