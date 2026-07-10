"""Main FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Import all models so SQLAlchemy sees them before create_all
    import app.models.chunk  # noqa: F401
    import app.models.document  # noqa: F401
    import app.models.generation  # noqa: F401
    import app.models.grade  # noqa: F401
    import app.models.semantic_cache  # noqa: F401

    from app.db.base import Base
    from app.db.session import engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="FactShield Edu RAG API",
        description="Factual consistency and active learning assistant.",
        version="1.0.0",
        lifespan=lifespan,
    )

    from app.core.rate_limit import limiter, RateLimitExceeded, _rate_limit_exceeded_handler
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api/v1")

    return app


app = create_app()
