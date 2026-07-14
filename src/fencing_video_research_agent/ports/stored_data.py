"""Read-only port contracts for inspecting stored research data."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class StoredVideoSummary:
    """Compact read model for listing stored videos."""

    youtube_video_id: str
    title: str
    channel_title: str
    published_at: datetime | None
    first_seen_at: datetime
    last_refreshed_at: datetime


@dataclass(frozen=True, slots=True)
class StoredVideoDetail:
    """Detailed read model for inspecting one stored video."""

    youtube_video_id: str
    title: str
    description: str | None
    channel_id: str
    channel_title: str
    published_at: datetime | None
    duration_seconds: int | None
    view_count: int | None
    like_count: int | None
    comment_count: int | None
    tags: tuple[str, ...]
    thumbnail_url: str | None
    video_url: str | None
    first_seen_at: datetime
    last_refreshed_at: datetime
    annotation_status: str | None


class StoredDataReader(Protocol):
    """Read-only boundary for inspecting stored videos."""

    def list_videos(self, *, limit: int) -> tuple[StoredVideoSummary, ...]:
        """Return stored video summaries ordered for inspection."""

    def get_video(self, youtube_video_id: str) -> StoredVideoDetail | None:
        """Return one stored video detail by YouTube ID, if present."""
