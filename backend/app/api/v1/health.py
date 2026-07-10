"""FastAPI router for application health and readiness probes."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok"}


@router.get("/readyz")
async def readyz() -> dict[str, str]:
    """Readiness probe."""
    return {"status": "ready"}
