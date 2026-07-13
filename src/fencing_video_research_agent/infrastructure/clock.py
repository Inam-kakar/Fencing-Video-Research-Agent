"""Infrastructure clock implementation."""

from __future__ import annotations

from datetime import UTC, datetime


class SystemClock:
    """Clock implementation backed by the system UTC time."""

    def utcnow(self) -> datetime:
        """Return the current timezone-aware UTC datetime."""

        return datetime.now(UTC)
