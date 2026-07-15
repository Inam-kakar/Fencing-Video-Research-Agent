"""Application use case for exporting search-hit provenance data."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fencing_video_research_agent.application.export_videos import InvalidExportFormatError
from fencing_video_research_agent.ports import (
    SearchHitExportFormat,
    SearchHitExportReader,
    SearchHitExportWriter,
)

DEFAULT_SEARCH_HIT_EXPORT_PATHS: dict[SearchHitExportFormat, Path] = {
    "csv": Path("data/exports/search_hits.csv"),
    "json": Path("data/exports/search_hits.json"),
}


@dataclass(frozen=True, slots=True)
class ExportSearchHitsRequest:
    """Input for exporting search-hit provenance rows."""

    export_format: str = "csv"
    output_path: Path | None = None
    overwrite: bool = False

    def __post_init__(self) -> None:
        normalized_format = self.export_format.strip().lower()
        if normalized_format not in DEFAULT_SEARCH_HIT_EXPORT_PATHS:
            raise InvalidExportFormatError(self.export_format)
        object.__setattr__(self, "export_format", normalized_format)


@dataclass(frozen=True, slots=True)
class ExportSearchHitsResult:
    """Summary of a completed search-hit provenance export."""

    output_path: Path
    row_count: int
    export_format: SearchHitExportFormat


class ExportSearchHitsUseCase:
    """Export one row per search-hit relationship without mutating stored data."""

    def __init__(
        self,
        *,
        reader: SearchHitExportReader,
        writer: SearchHitExportWriter,
    ) -> None:
        self._reader = reader
        self._writer = writer

    def execute(self, request: ExportSearchHitsRequest) -> ExportSearchHitsResult:
        """Write a search-hit provenance export file."""

        export_format = _search_hit_export_format(request.export_format)
        output_path = request.output_path or DEFAULT_SEARCH_HIT_EXPORT_PATHS[export_format]
        records = self._reader.read_search_hit_exports()
        write_result = self._writer.write_search_hits(
            records,
            output_path=output_path,
            export_format=export_format,
            overwrite=request.overwrite,
        )
        return ExportSearchHitsResult(
            output_path=write_result.output_path,
            row_count=write_result.row_count,
            export_format=write_result.export_format,
        )


def _search_hit_export_format(export_format: str) -> SearchHitExportFormat:
    if export_format == "csv":
        return "csv"
    if export_format == "json":
        return "json"
    raise InvalidExportFormatError(export_format)
