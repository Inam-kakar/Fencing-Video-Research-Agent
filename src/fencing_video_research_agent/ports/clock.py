"""Clock port for deterministic application-layer time handling."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol


class Clock(Protocol):
    """Boundary for obtaining the current UTC time."""

    def utcnow(self) -> datetime:
        """Return the current timezone-aware UTC datetime."""
