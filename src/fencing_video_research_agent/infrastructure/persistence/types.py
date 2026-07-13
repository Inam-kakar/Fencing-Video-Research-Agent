"""SQLAlchemy custom types for persistence-only concerns."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.types import DateTime, TypeDecorator


class UTCDateTime(TypeDecorator[datetime]):
    """Persist timezone-aware datetimes as UTC and return UTC-aware values."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        """Normalize aware datetimes to UTC before storing them."""

        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            msg = "datetime values must be timezone-aware"
            raise ValueError(msg)

        utc_value = value.astimezone(UTC)
        if dialect.name == "sqlite":
            return utc_value.replace(tzinfo=None)
        return utc_value

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        """Return timezone-aware UTC datetimes from persisted values."""

        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
