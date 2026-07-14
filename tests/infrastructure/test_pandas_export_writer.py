"""Tests for pandas-backed export writers."""

from __future__ import annotations

import csv
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from fencing_video_research_agent.infrastructure.exports import (
    VIDEO_EXPORT_COLUMNS,
    PandasVideoExportWriter,
)
from fencing_video_research_agent.ports import ExportFileExistsError, VideoExportRecord

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
        fencer_names=("Fencer One", "Fencer Two"),
        weapon_category="sabre",
        event_notes="Final bout",
        annotation_updated_at=NOW,
        discovery_run_count=2,
        first_collection_run_started_at=NOW,
        latest_collection_run_started_at=NOW,
        first_query_text="first sabre",
        latest_query_text="latest sabre",
    )


def test_csv_export_creates_directory_and_writes_expected_columns(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "nested" / "videos.csv"
    writer = PandasVideoExportWriter()

    result = writer.write_videos(
        [make_export_record()],
        output_path=output_path,
        export_format="csv",
        overwrite=False,
    )

    assert result.output_path == output_path
    assert result.row_count == 1
    assert output_path.exists()
    with output_path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    assert rows[0].keys() == set(VIDEO_EXPORT_COLUMNS)
    assert rows[0]["youtube_video_id"] == "video-123"
    assert rows[0]["tags"] == '["sabre", "final"]'
    assert rows[0]["fencer_names"] == '["Fencer One", "Fencer Two"]'
    assert rows[0]["published_at"] == "2026-07-14T10:00:00+00:00"
    assert len(rows) == 1


def test_json_export_writes_records_with_arrays(tmp_path: Path) -> None:
    output_path = tmp_path / "videos.json"
    writer = PandasVideoExportWriter()

    result = writer.write_videos(
        [make_export_record()],
        output_path=output_path,
        export_format="json",
        overwrite=False,
    )

    assert result.row_count == 1
    records = json.loads(output_path.read_text(encoding="utf-8"))
    assert records[0]["youtube_video_id"] == "video-123"
    assert records[0]["tags"] == ["sabre", "final"]
    assert records[0]["fencer_names"] == ["Fencer One", "Fencer Two"]
    assert records[0]["annotation_updated_at"] == "2026-07-14T10:00:00+00:00"


def test_empty_exports_have_headers_or_empty_records(tmp_path: Path) -> None:
    writer = PandasVideoExportWriter()
    csv_path = tmp_path / "empty.csv"
    json_path = tmp_path / "empty.json"

    csv_result = writer.write_videos(
        [],
        output_path=csv_path,
        export_format="csv",
        overwrite=False,
    )
    json_result = writer.write_videos(
        [],
        output_path=json_path,
        export_format="json",
        overwrite=False,
    )

    assert csv_result.row_count == 0
    assert csv_path.read_text(encoding="utf-8").splitlines()[0].split(",") == VIDEO_EXPORT_COLUMNS
    assert json_result.row_count == 0
    assert json.loads(json_path.read_text(encoding="utf-8")) == []


def test_existing_output_requires_overwrite(tmp_path: Path) -> None:
    output_path = tmp_path / "videos.csv"
    output_path.write_text("existing", encoding="utf-8")
    writer = PandasVideoExportWriter()

    with pytest.raises(ExportFileExistsError) as error:
        writer.write_videos(
            [make_export_record()],
            output_path=output_path,
            export_format="csv",
            overwrite=False,
        )

    assert error.value.output_path == output_path
    assert output_path.read_text(encoding="utf-8") == "existing"

    result = writer.write_videos(
        [make_export_record()],
        output_path=output_path,
        export_format="csv",
        overwrite=True,
    )

    assert result.row_count == 1
    assert "video-123" in output_path.read_text(encoding="utf-8")


def test_generated_data_exports_are_ignored_by_git() -> None:
    result = subprocess.run(
        ["git", "check-ignore", "data/exports/generated-test.csv"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
