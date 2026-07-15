"""SQLAlchemy readers for export-shaped research datasets."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload, sessionmaker

from fencing_video_research_agent.infrastructure.persistence.models import (
    CollectionRunRecord,
    ResearchAnnotationRecord,
    SearchHitRecord,
    VideoRecord,
    YouTubeVideoMetadataRecord,
)
from fencing_video_research_agent.ports import (
    IncompleteVideoRecordError,
    SearchHitExportRecord,
    VideoExportRecord,
)


class SqlAlchemyVideoExportReader:
    """Read export-ready video records from the local research database."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def read_video_exports(self) -> tuple[VideoExportRecord, ...]:
        """Return one export row per stored video."""

        with self._session_factory() as session:
            records = session.scalars(
                select(VideoRecord)
                .options(
                    joinedload(VideoRecord.youtube_metadata),
                    joinedload(VideoRecord.annotation),
                    selectinload(VideoRecord.search_hits)
                    .joinedload(SearchHitRecord.collection_run)
                    .joinedload(CollectionRunRecord.search_query),
                )
                .order_by(VideoRecord.first_seen_at.asc(), VideoRecord.youtube_video_id.asc())
            ).all()

        return tuple(_export_record_from_video(record) for record in records)


class SqlAlchemySearchHitExportReader:
    """Read export-ready search-hit provenance records from the local database."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def read_search_hit_exports(self) -> tuple[SearchHitExportRecord, ...]:
        """Return one export row per search hit."""

        with self._session_factory() as session:
            records = session.scalars(
                select(SearchHitRecord)
                .join(SearchHitRecord.collection_run)
                .options(
                    joinedload(SearchHitRecord.collection_run).joinedload(
                        CollectionRunRecord.search_query
                    ),
                    joinedload(SearchHitRecord.video).joinedload(VideoRecord.youtube_metadata),
                    joinedload(SearchHitRecord.video).joinedload(VideoRecord.annotation),
                )
                .order_by(
                    CollectionRunRecord.started_at.asc(),
                    CollectionRunRecord.id.asc(),
                    SearchHitRecord.rank.asc(),
                    SearchHitRecord.id.asc(),
                )
            ).all()

        return tuple(_search_hit_export_record_from_hit(record) for record in records)


def _export_record_from_video(record: VideoRecord) -> VideoExportRecord:
    metadata = _required_metadata(record)
    annotation = record.annotation
    provenance = _provenance_summary(record.search_hits)
    return VideoExportRecord(
        youtube_video_id=record.youtube_video_id,
        title=metadata.title,
        description=metadata.description,
        channel_id=metadata.channel_id,
        channel_title=metadata.channel_title,
        published_at=metadata.published_at,
        duration_seconds=metadata.duration_seconds,
        view_count=metadata.view_count,
        like_count=metadata.like_count,
        comment_count=metadata.comment_count,
        tags=tuple(metadata.tags or ()),
        thumbnail_url=metadata.thumbnail_url,
        video_url=metadata.video_url,
        first_seen_at=record.first_seen_at,
        last_refreshed_at=metadata.last_refreshed_at,
        review_status=_review_status(annotation),
        notes=None if annotation is None else annotation.notes,
        relevance_label=None if annotation is None else annotation.relevance_label,
        competition_name=None if annotation is None else annotation.competition_name,
        fencer_names=() if annotation is None else tuple(annotation.fencer_names or ()),
        weapon_category=None if annotation is None else annotation.weapon_category,
        event_notes=None if annotation is None else annotation.event_notes,
        annotation_updated_at=None if annotation is None else annotation.updated_at,
        discovery_run_count=provenance.discovery_run_count,
        first_collection_run_started_at=provenance.first_collection_run_started_at,
        latest_collection_run_started_at=provenance.latest_collection_run_started_at,
        first_query_text=provenance.first_query_text,
        latest_query_text=provenance.latest_query_text,
    )


def _search_hit_export_record_from_hit(record: SearchHitRecord) -> SearchHitExportRecord:
    video = record.video
    metadata = _required_metadata(video)
    annotation = video.annotation
    collection_run = record.collection_run
    search_query = collection_run.search_query
    return SearchHitExportRecord(
        collection_run_id=collection_run.id,
        query_text=search_query.query_text,
        query_parameters=dict(search_query.parameters or {}),
        query_fingerprint=search_query.parameters_fingerprint,
        run_started_at=collection_run.started_at,
        run_completed_at=collection_run.completed_at,
        run_status=collection_run.status,
        run_error_message=collection_run.error_message,
        discovered_at=record.discovered_at,
        rank=record.rank,
        youtube_video_id=video.youtube_video_id,
        title=metadata.title,
        channel_id=metadata.channel_id,
        channel_title=metadata.channel_title,
        published_at=metadata.published_at,
        duration_seconds=metadata.duration_seconds,
        view_count=metadata.view_count,
        like_count=metadata.like_count,
        comment_count=metadata.comment_count,
        video_url=metadata.video_url,
        last_refreshed_at=metadata.last_refreshed_at,
        review_status=_review_status(annotation),
        relevance_label=None if annotation is None else annotation.relevance_label,
    )


@dataclass(frozen=True, slots=True)
class _ProvenanceSummary:
    discovery_run_count: int
    first_collection_run_started_at: datetime | None
    latest_collection_run_started_at: datetime | None
    first_query_text: str | None
    latest_query_text: str | None


def _provenance_summary(search_hits: list[SearchHitRecord]) -> _ProvenanceSummary:
    ordered_hits = sorted(
        search_hits,
        key=lambda hit: (hit.collection_run.started_at, hit.collection_run.id),
    )
    if not ordered_hits:
        return _ProvenanceSummary(
            discovery_run_count=0,
            first_collection_run_started_at=None,
            latest_collection_run_started_at=None,
            first_query_text=None,
            latest_query_text=None,
        )

    first_run = ordered_hits[0].collection_run
    latest_run = ordered_hits[-1].collection_run
    return _ProvenanceSummary(
        discovery_run_count=len({hit.collection_run_id for hit in ordered_hits}),
        first_collection_run_started_at=first_run.started_at,
        latest_collection_run_started_at=latest_run.started_at,
        first_query_text=first_run.search_query.query_text,
        latest_query_text=latest_run.search_query.query_text,
    )


def _review_status(annotation: ResearchAnnotationRecord | None) -> str | None:
    if annotation is None:
        return None
    return annotation.review_status


def _required_metadata(record: VideoRecord) -> YouTubeVideoMetadataRecord:
    metadata = record.youtube_metadata
    if metadata is None:
        msg = f"video has no YouTube metadata: {record.youtube_video_id}"
        raise IncompleteVideoRecordError(msg)
    return metadata
