"""Declarative base, UTC-aware datetime column and the shared timestamp helper."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    DateTime,
    TypeDecorator,
)
from sqlalchemy.orm import DeclarativeBase


def utcnow() -> datetime:
    return datetime.now(UTC)


class UTCDateTime(TypeDecorator):
    """Store timezone-aware datetimes as naive UTC in SQLite and restore tzinfo on load."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is not None:
            value = value.astimezone(UTC).replace(tzinfo=None)
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return value.replace(tzinfo=UTC)


class Base(DeclarativeBase):
    pass
