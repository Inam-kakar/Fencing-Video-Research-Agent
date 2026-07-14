"""Port contracts for research data exports."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal, Protocol

type VideoExportFormat = Literal["csv", "json"]


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
class VideoExportWriteResult:
    """Result from writing an export file."""

    output_path: Path
    row_count: int
    export_format: VideoExportFormat


class ExportFileExistsError(Exception):
    """Raised when an export would overwrite an existing file without approval."""

    def __init__(self, output_path: Path) -> None:
        self.output_path = output_path
        super().__init__(f"export file already exists: {output_path}")


class VideoExportReader(Protocol):
    """Read-only boundary for export-shaped stored video records."""

    def read_video_exports(self) -> tuple[VideoExportRecord, ...]:
        """Return one export record per stored video."""


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
