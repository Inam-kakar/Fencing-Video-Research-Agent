"""Port contracts for research data exports."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal, Protocol

type VideoExportFormat = Literal["csv", "json"]
type SearchHitExportFormat = Literal["csv", "json"]


@dataclass(frozen=True, slots=True)
class VideoExportRecord:
    """One export-ready row for a stored video."""

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
    review_status: str | None
    notes: str | None
    relevance_label: str | None
    competition_name: str | None
    fencer_names: tuple[str, ...]
    weapon_category: str | None
    event_notes: str | None
    annotation_updated_at: datetime | None
    discovery_run_count: int
    first_collection_run_started_at: datetime | None
    latest_collection_run_started_at: datetime | None
    first_query_text: str | None
    latest_query_text: str | None


@dataclass(frozen=True, slots=True)
class SearchHitExportRecord:
    """One export-ready row for a collection-run search hit."""

    collection_run_id: int
    query_text: str
    query_parameters: dict[str, object]
    query_fingerprint: str
    run_started_at: datetime
    run_completed_at: datetime | None
    run_status: str
    run_error_message: str | None
    discovered_at: datetime
    rank: int | None
    youtube_video_id: str
    title: str
    channel_id: str
    channel_title: str
    published_at: datetime | None
    duration_seconds: int | None
    view_count: int | None
    like_count: int | None
    comment_count: int | None
    video_url: str | None
    last_refreshed_at: datetime
    review_status: str | None
    relevance_label: str | None


@dataclass(frozen=True, slots=True)
class VideoExportWriteResult:
    """Result from writing an export file."""

    output_path: Path
    row_count: int
    export_format: VideoExportFormat


@dataclass(frozen=True, slots=True)
class SearchHitExportWriteResult:
    """Result from writing a search-hit provenance export file."""

    output_path: Path
    row_count: int
    export_format: SearchHitExportFormat


class ExportFileExistsError(Exception):
    """Raised when an export would overwrite an existing file without approval."""

    def __init__(self, output_path: Path) -> None:
        self.output_path = output_path
        super().__init__(f"export file already exists: {output_path}")


class VideoExportReader(Protocol):
    """Read-only boundary for export-shaped stored video records."""

    def read_video_exports(self) -> tuple[VideoExportRecord, ...]:
        """Return one export record per stored video."""


class SearchHitExportReader(Protocol):
    """Read-only boundary for export-shaped search-hit provenance records."""

    def read_search_hit_exports(self) -> tuple[SearchHitExportRecord, ...]:
        """Return one export record per search hit."""


class VideoExportWriter(Protocol):
    """Boundary for writing video export records to a file."""

    def write_videos(
        self,
        records: Sequence[VideoExportRecord],
        *,
        output_path: Path,
        export_format: VideoExportFormat,
        overwrite: bool,
    ) -> VideoExportWriteResult:
        """Write video export records to the requested output path."""


class SearchHitExportWriter(Protocol):
    """Boundary for writing search-hit export records to a file."""

    def write_search_hits(
        self,
        records: Sequence[SearchHitExportRecord],
        *,
        output_path: Path,
        export_format: SearchHitExportFormat,
        overwrite: bool,
    ) -> SearchHitExportWriteResult:
        """Write search-hit export records to the requested output path."""
