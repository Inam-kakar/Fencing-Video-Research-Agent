"""Tests for video export application use case."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import pytest

from fencing_video_research_agent.application import (
    ExportVideosRequest,
    ExportVideosUseCase,
    InvalidExportFormatError,
)
from fencing_video_research_agent.ports import (
    VideoExportFormat,
    VideoExportRecord,
    VideoExportWriteResult,
)

NOW = datetime(2026, 7, 14, 10, 0, tzinfo=UTC)


def make_export_record(youtube_video_id: str = "video-123") -> VideoExportRecord:
    """Create one export-ready video record."""

    return VideoExportRecord(
        youtube_video_id=youtube_video_id,
        title="Sabre final",
        description="A public fencing bout.",
        channel_id="channel-123",
        channel_title="Fencing Channel",
        published_at=NOW,
        duration_seconds=720,
        view_count=100,
        like_count=None,
        comment_count=5,
        tags=("sabre", "final"),
        thumbnail_url="https://example.test/thumb.jpg",
        video_url=f"https://www.youtube.com/watch?v={youtube_video_id}",
        first_seen_at=NOW,
        last_refreshed_at=NOW,
        review_status="reviewed",
        notes="Useful reference.",
        relevance_label="relevant",
        competition_name="European Championship",
        fencer_names=("Fencer One",),
        weapon_category="sabre",
        event_notes="Final bout",
        annotation_updated_at=NOW,
        discovery_run_count=2,
        first_collection_run_started_at=NOW,
        latest_collection_run_started_at=NOW,
        first_query_text="first sabre",
        latest_query_text="latest sabre",
    )


@dataclass
class FakeVideoExportReader:
    """Fake export reader for application tests."""

    records: tuple[VideoExportRecord, ...] = ()
    read_count: int = 0

    def read_video_exports(self) -> tuple[VideoExportRecord, ...]:
        self.read_count += 1
        return self.records


@dataclass
class FakeVideoExportWriter:
    """Fake export writer for application tests."""

    calls: list[tuple[Sequence[VideoExportRecord], Path, VideoExportFormat, bool]] = field(
        default_factory=list
    )

    def write_videos(
        self,
        records: Sequence[VideoExportRecord],
        *,
        output_path: Path,
        export_format: VideoExportFormat,
        overwrite: bool,
    ) -> VideoExportWriteResult:
        self.calls.append((records, output_path, export_format, overwrite))
        return VideoExportWriteResult(
            output_path=output_path,
            row_count=len(records),
            export_format=export_format,
        )


def test_export_videos_uses_default_csv_path() -> None:
    reader = FakeVideoExportReader(records=(make_export_record(),))
    writer = FakeVideoExportWriter()
    use_case = ExportVideosUseCase(reader=reader, writer=writer)

    result = use_case.execute(ExportVideosRequest())

    assert result.output_path == Path("data/exports/videos.csv")
    assert result.row_count == 1
    assert result.export_format == "csv"
    assert reader.read_count == 1
    assert writer.calls == [
        (reader.records, Path("data/exports/videos.csv"), "csv", False),
    ]


def test_export_videos_uses_default_json_path() -> None:
    reader = FakeVideoExportReader()
    writer = FakeVideoExportWriter()
    use_case = ExportVideosUseCase(reader=reader, writer=writer)

    result = use_case.execute(ExportVideosRequest(export_format="json"))

    assert result.output_path == Path("data/exports/videos.json")
    assert result.export_format == "json"


def test_export_videos_allows_output_override_and_overwrite() -> None:
    reader = FakeVideoExportReader(records=(make_export_record(),))
    writer = FakeVideoExportWriter()
    use_case = ExportVideosUseCase(reader=reader, writer=writer)
    output_path = Path("tmp/custom.csv")

    result = use_case.execute(
        ExportVideosRequest(
            export_format="csv",
            output_path=output_path,
            overwrite=True,
        )
    )

    assert result.output_path == output_path
    assert writer.calls == [(reader.records, output_path, "csv", True)]


def test_export_videos_rejects_unknown_format() -> None:
    with pytest.raises(InvalidExportFormatError):
        ExportVideosRequest(export_format="xlsx")
