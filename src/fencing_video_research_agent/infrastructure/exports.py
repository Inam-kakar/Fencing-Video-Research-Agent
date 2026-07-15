"""Pandas-backed export writers for research datasets."""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import datetime
from importlib import import_module
from pathlib import Path
from typing import Any

from fencing_video_research_agent.ports import (
    ExportFileExistsError,
    SearchHitExportFormat,
    SearchHitExportRecord,
    SearchHitExportWriteResult,
    VideoExportFormat,
    VideoExportRecord,
    VideoExportWriteResult,
)

VIDEO_EXPORT_COLUMNS = [
    "youtube_video_id",
    "title",
    "description",
    "channel_id",
    "channel_title",
    "published_at",
    "duration_seconds",
    "view_count",
    "like_count",
    "comment_count",
    "tags",
    "thumbnail_url",
    "video_url",
    "first_seen_at",
    "last_refreshed_at",
    "review_status",
    "notes",
    "relevance_label",
    "competition_name",
    "fencer_names",
    "weapon_category",
    "event_notes",
    "annotation_updated_at",
    "discovery_run_count",
    "first_collection_run_started_at",
    "latest_collection_run_started_at",
    "first_query_text",
    "latest_query_text",
]

SEARCH_HIT_EXPORT_COLUMNS = [
    "collection_run_id",
    "query_text",
    "query_parameters",
    "query_fingerprint",
    "run_started_at",
    "run_completed_at",
    "run_status",
    "run_error_message",
    "discovered_at",
    "rank",
    "youtube_video_id",
    "title",
    "channel_id",
    "channel_title",
    "published_at",
    "duration_seconds",
    "view_count",
    "like_count",
    "comment_count",
    "video_url",
    "last_refreshed_at",
    "review_status",
    "relevance_label",
]


class PandasVideoExportWriter:
    """Write video export records to CSV or JSON using pandas."""

    def write_videos(
        self,
        records: Sequence[VideoExportRecord],
        *,
        output_path: Path,
        export_format: VideoExportFormat,
        overwrite: bool,
    ) -> VideoExportWriteResult:
        """Write video export records to the requested file."""

        output_path = Path(output_path)
        if output_path.exists() and not overwrite:
            raise ExportFileExistsError(output_path)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        rows = [_record_to_row(record, csv_format=export_format == "csv") for record in records]
        pandas: Any = import_module("pandas")
        frame = pandas.DataFrame(rows, columns=VIDEO_EXPORT_COLUMNS)

        if export_format == "csv":
            frame.to_csv(output_path, index=False)
        else:
            frame.to_json(output_path, orient="records", indent=2, force_ascii=False)

        return VideoExportWriteResult(
            output_path=output_path,
            row_count=len(records),
            export_format=export_format,
        )


class PandasSearchHitExportWriter:
    """Write search-hit provenance export records to CSV or JSON using pandas."""

    def write_search_hits(
        self,
        records: Sequence[SearchHitExportRecord],
        *,
        output_path: Path,
        export_format: SearchHitExportFormat,
        overwrite: bool,
    ) -> SearchHitExportWriteResult:
        """Write search-hit export records to the requested file."""

        output_path = Path(output_path)
        if output_path.exists() and not overwrite:
            raise ExportFileExistsError(output_path)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        rows = [
            _search_hit_record_to_row(record, csv_format=export_format == "csv")
            for record in records
        ]
        pandas: Any = import_module("pandas")
        frame = pandas.DataFrame(rows, columns=SEARCH_HIT_EXPORT_COLUMNS)

        if export_format == "csv":
            frame.to_csv(output_path, index=False)
        else:
            frame.to_json(output_path, orient="records", indent=2, force_ascii=False)

        return SearchHitExportWriteResult(
            output_path=output_path,
            row_count=len(records),
            export_format=export_format,
        )


def _record_to_row(record: VideoExportRecord, *, csv_format: bool) -> dict[str, Any]:
    tags: list[str] | str = list(record.tags)
    fencer_names: list[str] | str = list(record.fencer_names)
    if csv_format:
        tags = _json_string(record.tags)
        fencer_names = _json_string(record.fencer_names)

    return {
        "youtube_video_id": record.youtube_video_id,
        "title": record.title,
        "description": record.description,
        "channel_id": record.channel_id,
        "channel_title": record.channel_title,
        "published_at": _datetime_string(record.published_at),
        "duration_seconds": record.duration_seconds,
        "view_count": record.view_count,
        "like_count": record.like_count,
        "comment_count": record.comment_count,
        "tags": tags,
        "thumbnail_url": record.thumbnail_url,
        "video_url": record.video_url,
        "first_seen_at": _datetime_string(record.first_seen_at),
        "last_refreshed_at": _datetime_string(record.last_refreshed_at),
        "review_status": record.review_status,
        "notes": record.notes,
        "relevance_label": record.relevance_label,
        "competition_name": record.competition_name,
        "fencer_names": fencer_names,
        "weapon_category": record.weapon_category,
        "event_notes": record.event_notes,
        "annotation_updated_at": _datetime_string(record.annotation_updated_at),
        "discovery_run_count": record.discovery_run_count,
        "first_collection_run_started_at": _datetime_string(record.first_collection_run_started_at),
        "latest_collection_run_started_at": _datetime_string(
            record.latest_collection_run_started_at
        ),
        "first_query_text": record.first_query_text,
        "latest_query_text": record.latest_query_text,
    }


def _search_hit_record_to_row(
    record: SearchHitExportRecord,
    *,
    csv_format: bool,
) -> dict[str, Any]:
    query_parameters: dict[str, object] | str = dict(record.query_parameters)
    if csv_format:
        query_parameters = json.dumps(record.query_parameters, ensure_ascii=False, sort_keys=True)

    return {
        "collection_run_id": record.collection_run_id,
        "query_text": record.query_text,
        "query_parameters": query_parameters,
        "query_fingerprint": record.query_fingerprint,
        "run_started_at": _datetime_string(record.run_started_at),
        "run_completed_at": _datetime_string(record.run_completed_at),
        "run_status": record.run_status,
        "run_error_message": record.run_error_message,
        "discovered_at": _datetime_string(record.discovered_at),
        "rank": record.rank,
        "youtube_video_id": record.youtube_video_id,
        "title": record.title,
        "channel_id": record.channel_id,
        "channel_title": record.channel_title,
        "published_at": _datetime_string(record.published_at),
        "duration_seconds": record.duration_seconds,
        "view_count": record.view_count,
        "like_count": record.like_count,
        "comment_count": record.comment_count,
        "video_url": record.video_url,
        "last_refreshed_at": _datetime_string(record.last_refreshed_at),
        "review_status": record.review_status,
        "relevance_label": record.relevance_label,
    }


def _datetime_string(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _json_string(values: tuple[str, ...]) -> str:
    return json.dumps(list(values), ensure_ascii=False)
