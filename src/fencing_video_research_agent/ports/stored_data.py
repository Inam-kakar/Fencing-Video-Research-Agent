"""Read-only port contracts for inspecting stored research data."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Protocol

from fencing_video_research_agent.ports.repositories import CollectionRunRecordId


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


@dataclass(frozen=True, slots=True)
class StoredCollectionRunSummary:
    """Compact read model for listing stored collection runs."""

    run_id: CollectionRunRecordId
    query_text: str
    status: str
    started_at: datetime
    completed_at: datetime | None
    hit_count: int


@dataclass(frozen=True, slots=True)
class StoredCollectionRunHit:
    """Read model for one video returned by a collection run."""

    rank: int | None
    youtube_video_id: str
    title: str
    channel_title: str


@dataclass(frozen=True, slots=True)
class StoredCollectionRunDetail:
    """Detailed read model for inspecting one collection run."""

    run_id: CollectionRunRecordId
    query_text: str
    query_parameters: Mapping[str, object]
    status: str
    started_at: datetime
    completed_at: datetime | None
    hit_count: int
    hits: tuple[StoredCollectionRunHit, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "query_parameters",
            MappingProxyType(dict(self.query_parameters)),
        )


class StoredDataReader(Protocol):
    """Read-only boundary for inspecting stored research data."""

    def list_videos(self, *, limit: int) -> tuple[StoredVideoSummary, ...]:
        """Return stored video summaries ordered for inspection."""

    def get_video(self, youtube_video_id: str) -> StoredVideoDetail | None:
        """Return one stored video detail by YouTube ID, if present."""

    def list_collection_runs(self, *, limit: int) -> tuple[StoredCollectionRunSummary, ...]:
        """Return stored collection-run summaries ordered for inspection."""

    def get_collection_run(
        self,
        run_id: CollectionRunRecordId,
    ) -> StoredCollectionRunDetail | None:
        """Return one stored collection-run detail by run ID, if present."""
