"""Application use case for exporting stored video research data."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fencing_video_research_agent.ports import (
    VideoExportFormat,
    VideoExportReader,
    VideoExportWriter,
)

DEFAULT_VIDEO_EXPORT_PATHS: dict[VideoExportFormat, Path] = {
    "csv": Path("data/exports/videos.csv"),
    "json": Path("data/exports/videos.json"),
}


@dataclass(frozen=True, slots=True)
class ExportVideosRequest:
    """Input for exporting stored videos."""

    export_format: str = "csv"
    output_path: Path | None = None
    overwrite: bool = False

    def __post_init__(self) -> None:
        normalized_format = self.export_format.strip().lower()
        if normalized_format not in DEFAULT_VIDEO_EXPORT_PATHS:
            raise InvalidExportFormatError(self.export_format)
        object.__setattr__(self, "export_format", normalized_format)


@dataclass(frozen=True, slots=True)
class ExportVideosResult:
    """Summary of a completed video export."""

    output_path: Path
    row_count: int
    export_format: VideoExportFormat


class InvalidExportFormatError(ValueError):
    """Raised when an export format is unsupported."""

    def __init__(self, export_format: str) -> None:
        self.export_format = export_format
        super().__init__("export format must be csv or json")


class ExportVideosUseCase:
    """Export stored video metadata, annotations, and compact provenance."""

    def __init__(
        self,
        *,
        reader: VideoExportReader,
        writer: VideoExportWriter,
    ) -> None:
        self._reader = reader
        self._writer = writer

    def execute(self, request: ExportVideosRequest) -> ExportVideosResult:
        """Write a video export file without mutating stored database data."""

        export_format = _video_export_format(request.export_format)
        output_path = request.output_path or DEFAULT_VIDEO_EXPORT_PATHS[export_format]
        records = self._reader.read_video_exports()
        write_result = self._writer.write_videos(
            records,
            output_path=output_path,
            export_format=export_format,
            overwrite=request.overwrite,
        )
        return ExportVideosResult(
            output_path=write_result.output_path,
            row_count=write_result.row_count,
            export_format=write_result.export_format,
        )


def _video_export_format(export_format: str) -> VideoExportFormat:
    if export_format == "csv":
        return "csv"
    if export_format == "json":
        return "json"
    raise InvalidExportFormatError(export_format)
