"""Main v1 API router.

Aggregates all student, teacher, documents, health, and debug sub-routers.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import debug, documents, health, student, teacher

api_router = APIRouter()

api_router.include_router(student.router, prefix="/student", tags=["student"])
api_router.include_router(teacher.router, prefix="/teacher", tags=["teacher"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(health.router, tags=["health"])
api_router.include_router(debug.router, prefix="/debug", tags=["debug"])
