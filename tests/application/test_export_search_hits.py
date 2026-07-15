"""Tests for search-hit provenance export application use case."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import pytest

from fencing_video_research_agent.application import (
    ExportSearchHitsRequest,
    ExportSearchHitsUseCase,
    InvalidExportFormatError,
)
from fencing_video_research_agent.ports import (
    SearchHitExportFormat,
    SearchHitExportRecord,
    SearchHitExportWriteResult,
)

NOW = datetime(2026, 7, 14, 10, 0, tzinfo=UTC)


def make_search_hit_export_record() -> SearchHitExportRecord:
    """Create one export-ready search-hit record."""

    return SearchHitExportRecord(
        collection_run_id=1,
        query_text="sabre fencing final",
        query_parameters={"order": "relevance"},
        query_fingerprint="abc123",
        run_started_at=NOW,
        run_completed_at=NOW,
        run_status="completed",
        run_error_message=None,
        discovered_at=NOW,
        rank=1,
        youtube_video_id="video-123",
        title="Sabre final",
        channel_id="channel-123",
        channel_title="Fencing Channel",
        published_at=NOW,
        duration_seconds=720,
        view_count=100,
        like_count=None,
        comment_count=5,
        video_url="https://www.youtube.com/watch?v=video-123",
        last_refreshed_at=NOW,
        review_status="reviewed",
        relevance_label="relevant",
    )


@dataclass
class FakeSearchHitExportReader:
    """Fake export reader for application tests."""

    records: tuple[SearchHitExportRecord, ...] = ()
    read_count: int = 0

    def read_search_hit_exports(self) -> tuple[SearchHitExportRecord, ...]:
        self.read_count += 1
        return self.records


@dataclass
class FakeSearchHitExportWriter:
    """Fake export writer for application tests."""

    calls: list[tuple[Sequence[SearchHitExportRecord], Path, SearchHitExportFormat, bool]] = field(
        default_factory=list
    )

    def write_search_hits(
        self,
        records: Sequence[SearchHitExportRecord],
        *,
        output_path: Path,
        export_format: SearchHitExportFormat,
        overwrite: bool,
    ) -> SearchHitExportWriteResult:
        self.calls.append((records, output_path, export_format, overwrite))
        return SearchHitExportWriteResult(
            output_path=output_path,
            row_count=len(records),
            export_format=export_format,
        )


def test_export_search_hits_uses_default_csv_path() -> None:
    reader = FakeSearchHitExportReader(records=(make_search_hit_export_record(),))
    writer = FakeSearchHitExportWriter()
    use_case = ExportSearchHitsUseCase(reader=reader, writer=writer)

    result = use_case.execute(ExportSearchHitsRequest())

    assert result.output_path == Path("data/exports/search_hits.csv")
    assert result.row_count == 1
    assert result.export_format == "csv"
    assert reader.read_count == 1
    assert writer.calls == [
        (reader.records, Path("data/exports/search_hits.csv"), "csv", False),
    ]


def test_export_search_hits_uses_default_json_path() -> None:
    reader = FakeSearchHitExportReader()
    writer = FakeSearchHitExportWriter()
    use_case = ExportSearchHitsUseCase(reader=reader, writer=writer)

    result = use_case.execute(ExportSearchHitsRequest(export_format="json"))

    assert result.output_path == Path("data/exports/search_hits.json")
    assert result.export_format == "json"


def test_export_search_hits_allows_output_override_and_overwrite() -> None:
    reader = FakeSearchHitExportReader(records=(make_search_hit_export_record(),))
    writer = FakeSearchHitExportWriter()
    use_case = ExportSearchHitsUseCase(reader=reader, writer=writer)
    output_path = Path("tmp/custom-search-hits.csv")

    result = use_case.execute(
        ExportSearchHitsRequest(
            export_format="csv",
            output_path=output_path,
            overwrite=True,
        )
    )

    assert result.output_path == output_path
    assert writer.calls == [(reader.records, output_path, "csv", True)]


def test_export_search_hits_rejects_unknown_format() -> None:
    with pytest.raises(InvalidExportFormatError):
        ExportSearchHitsRequest(export_format="xlsx")
