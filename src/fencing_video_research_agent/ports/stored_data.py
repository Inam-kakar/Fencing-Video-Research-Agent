"""Read-only port contracts for inspecting stored research data."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Protocol

from fencing_video_research_agent.ports.repositories import CollectionRunRecordId


@dataclass(frozen=True, slots=True)
class StoredDataSummary:
    """Dashboard-oriented counts for stored research data."""

    video_count: int
    collection_run_count: int
    search_hit_count: int
    annotation_count: int
    reviewed_count: int
    unreviewed_count: int


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
    relevance_label: str | None = None
    notes: str | None = None
    competition_name: str | None = None
    fencer_names: tuple[str, ...] = ()
    weapon_category: str | None = None
    event_notes: str | None = None
    annotation_updated_at: datetime | None = None
    discovery_run_count: int = 0
    first_collection_run_started_at: datetime | None = None
    latest_collection_run_started_at: datetime | None = None
    first_query_text: str | None = None
    latest_query_text: str | None = None


@dataclass(frozen=True, slots=True)
class StoredVideoTableRow:
    """Read model for one row in a frontend stored-video table."""

    youtube_video_id: str
    title: str
    channel_title: str
    duration_seconds: int | None
    published_at: datetime | None
    view_count: int | None
    review_status: str | None
    relevance_label: str | None
    video_url: str | None
    first_seen_at: datetime
    last_refreshed_at: datetime


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


@dataclass(frozen=True, slots=True)
class StoredSearchHitTableRow:
    """Read model for one row in a frontend search-hit provenance table."""

    collection_run_id: CollectionRunRecordId
    query_text: str
    run_started_at: datetime
    rank: int | None
    discovered_at: datetime
    youtube_video_id: str
    title: str
    channel_title: str
    review_status: str | None
    relevance_label: str | None


class StoredDataReader(Protocol):
    """Read-only boundary for inspecting stored research data."""

    def get_summary(self) -> StoredDataSummary:
        """Return dashboard-oriented stored-data counts."""

    def list_videos(self, *, limit: int) -> tuple[StoredVideoSummary, ...]:
        """Return stored video summaries ordered for inspection."""

    def list_video_table_rows(
        self,
        *,
        limit: int,
        offset: int,
        search: str | None,
    ) -> tuple[StoredVideoTableRow, ...]:
        """Return API-friendly stored-video table rows."""

    def get_video(self, youtube_video_id: str) -> StoredVideoDetail | None:
        """Return one stored video detail by YouTube ID, if present."""

    def list_collection_runs(
        self,
        *,
        limit: int,
        offset: int = 0,
    ) -> tuple[StoredCollectionRunSummary, ...]:
        """Return stored collection-run summaries ordered for inspection."""

    def get_collection_run(
        self,
        run_id: CollectionRunRecordId,
    ) -> StoredCollectionRunDetail | None:
        """Return one stored collection-run detail by run ID, if present."""

    def list_search_hit_table_rows(
        self,
        *,
        limit: int,
        offset: int,
        query_text: str | None,
    ) -> tuple[StoredSearchHitTableRow, ...]:
        """Return API-friendly search-hit provenance table rows."""
