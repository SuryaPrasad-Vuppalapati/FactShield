"""Base class for all SQLAlchemy ORM models."""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base class for SQLAlchemy models."""

    pass
