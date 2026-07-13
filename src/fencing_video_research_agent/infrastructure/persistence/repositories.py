"""SQLAlchemy repository implementations for Phase 1 persistence."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from fencing_video_research_agent.domain import (
    CollectionRun,
    ResearchAnnotation,
    ReviewStatus,
    SearchParameterValue,
    SearchQuery,
    Video,
    YouTubeMetadata,
)
from fencing_video_research_agent.infrastructure.persistence.models import (
    CollectionRunRecord,
    ResearchAnnotationRecord,
    SearchHitRecord,
    SearchQueryRecord,
    VideoRecord,
    YouTubeVideoMetadataRecord,
)
from fencing_video_research_agent.ports import (
    CollectionRunNotFoundError,
    CollectionRunRecordId,
    IncompleteVideoRecordError,
    SearchQueryRecordId,
    VideoNotFoundError,
    VideoRecordId,
)


class SqlAlchemyVideoRepository:
    """SQLAlchemy implementation of the video repository port."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_youtube_id(self, youtube_video_id: str) -> Video | None:
        """Return a domain video by YouTube ID, if it exists."""

        record = self._session.scalars(
            select(VideoRecord)
            .where(VideoRecord.youtube_video_id == youtube_video_id)
            .options(joinedload(VideoRecord.youtube_metadata))
        ).one_or_none()
        if record is None:
            return None
        return _video_from_record(record)

    def add_or_update(self, video: Video) -> VideoRecordId:
        """Insert a video or update its latest metadata."""

        record = self._session.scalars(
            select(VideoRecord)
            .where(VideoRecord.youtube_video_id == video.youtube_video_id)
            .options(joinedload(VideoRecord.youtube_metadata))
        ).one_or_none()

        if record is None:
            record = VideoRecord(
                youtube_video_id=video.youtube_video_id,
                first_seen_at=video.first_seen_at,
            )
            record.youtube_metadata = _metadata_record_from_domain(video.metadata)
            self._session.add(record)
        elif record.youtube_metadata is None:
            record.youtube_metadata = _metadata_record_from_domain(video.metadata)
        else:
            _update_metadata_record(record.youtube_metadata, video.metadata)

        self._session.flush()
        return VideoRecordId(record.id)


class SqlAlchemyCollectionRepository:
    """SQLAlchemy implementation for search queries, runs, and hits."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_or_create_search_query(
        self,
        query: SearchQuery,
        *,
        created_at: datetime,
    ) -> SearchQueryRecordId:
        """Return the existing search query handle or create one."""

        fingerprint = search_parameters_fingerprint(query.parameters)
        record = self._session.scalars(
            select(SearchQueryRecord).where(
                SearchQueryRecord.query_text == query.query_text,
                SearchQueryRecord.parameters_fingerprint == fingerprint,
            )
        ).one_or_none()

        if record is None:
            record = SearchQueryRecord(
                query_text=query.query_text,
                parameters=dict(query.parameters),
                parameters_fingerprint=fingerprint,
                created_at=created_at,
            )
            self._session.add(record)
            self._session.flush()

        return SearchQueryRecordId(record.id)

    def add_collection_run(
        self,
        run: CollectionRun,
        *,
        status: str,
        error_message: str | None = None,
    ) -> CollectionRunRecordId:
        """Record one collection run for the run's search query."""

        status = status.strip()
        if not status:
            msg = "status must not be empty"
            raise ValueError(msg)

        search_query_id = self.get_or_create_search_query(
            run.search_query,
            created_at=run.started_at,
        )
        record = CollectionRunRecord(
            search_query_id=int(search_query_id),
            started_at=run.started_at,
            completed_at=run.completed_at,
            status=status,
            error_message=error_message,
        )
        self._session.add(record)
        self._session.flush()
        return CollectionRunRecordId(record.id)

    def add_search_hit(
        self,
        collection_run_id: CollectionRunRecordId,
        *,
        youtube_video_id: str,
        discovered_at: datetime,
        rank: int | None = None,
    ) -> None:
        """Record that one collection run returned one stored video."""

        run_record = self._session.get(CollectionRunRecord, int(collection_run_id))
        if run_record is None:
            msg = f"collection run does not exist: {int(collection_run_id)}"
            raise CollectionRunNotFoundError(msg)

        video_record = self._session.scalars(
            select(VideoRecord).where(VideoRecord.youtube_video_id == youtube_video_id)
        ).one_or_none()
        if video_record is None:
            msg = f"video does not exist: {youtube_video_id}"
            raise VideoNotFoundError(msg)

        existing_hit = self._session.scalars(
            select(SearchHitRecord).where(
                SearchHitRecord.collection_run_id == int(collection_run_id),
                SearchHitRecord.video_id == video_record.id,
            )
        ).one_or_none()
        if existing_hit is not None:
            return

        self._session.add(
            SearchHitRecord(
                collection_run_id=int(collection_run_id),
                video_id=video_record.id,
                discovered_at=discovered_at,
                rank=rank,
            )
        )
        self._session.flush()


class SqlAlchemyAnnotationRepository:
    """SQLAlchemy implementation of the annotation repository port."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_youtube_id(self, youtube_video_id: str) -> ResearchAnnotation | None:
        """Return the annotation for a YouTube video, if it exists."""

        video_record = self._session.scalars(
            select(VideoRecord)
            .where(VideoRecord.youtube_video_id == youtube_video_id)
            .options(joinedload(VideoRecord.annotation))
        ).one_or_none()
        if video_record is None or video_record.annotation is None:
            return None
        return _annotation_from_record(video_record.annotation, video_record.youtube_video_id)

    def save(self, annotation: ResearchAnnotation) -> None:
        """Insert or update a researcher annotation."""

        video_record = self._session.scalars(
            select(VideoRecord)
            .where(VideoRecord.youtube_video_id == annotation.youtube_video_id)
            .options(joinedload(VideoRecord.annotation))
        ).one_or_none()
        if video_record is None:
            msg = f"video does not exist: {annotation.youtube_video_id}"
            raise VideoNotFoundError(msg)

        if video_record.annotation is None:
            video_record.annotation = ResearchAnnotationRecord(
                review_status=annotation.review_status.value,
                notes=annotation.notes,
                relevance_label=annotation.relevance_label,
                competition_name=annotation.competition_name,
                fencer_names=list(annotation.fencer_names),
                weapon_category=annotation.weapon_category,
                event_notes=annotation.event_notes,
                updated_at=annotation.updated_at,
            )
        else:
            _update_annotation_record(video_record.annotation, annotation)
        self._session.flush()


def search_parameters_fingerprint(
    parameters: Mapping[str, SearchParameterValue],
) -> str:
    """Return a stable SHA-256 fingerprint for search parameters."""

    canonical_parameters = json.dumps(
        dict(parameters),
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical_parameters.encode("utf-8")).hexdigest()


def _metadata_record_from_domain(metadata: YouTubeMetadata) -> YouTubeVideoMetadataRecord:
    return YouTubeVideoMetadataRecord(
        title=metadata.title,
        description=metadata.description,
        channel_id=metadata.channel_id,
        channel_title=metadata.channel_title,
        published_at=metadata.published_at,
        duration_seconds=_duration_seconds(metadata.duration),
        view_count=metadata.view_count,
        like_count=metadata.like_count,
        comment_count=metadata.comment_count,
        tags=list(metadata.tags),
        thumbnail_url=metadata.thumbnail_url,
        video_url=metadata.video_url,
        last_refreshed_at=metadata.last_refreshed_at,
    )


def _update_metadata_record(
    record: YouTubeVideoMetadataRecord,
    metadata: YouTubeMetadata,
) -> None:
    record.title = metadata.title
    record.description = metadata.description
    record.channel_id = metadata.channel_id
    record.channel_title = metadata.channel_title
    record.published_at = metadata.published_at
    record.duration_seconds = _duration_seconds(metadata.duration)
    record.view_count = metadata.view_count
    record.like_count = metadata.like_count
    record.comment_count = metadata.comment_count
    record.tags = list(metadata.tags)
    record.thumbnail_url = metadata.thumbnail_url
    record.video_url = metadata.video_url
    record.last_refreshed_at = metadata.last_refreshed_at


def _video_from_record(record: VideoRecord) -> Video:
    metadata_record = record.youtube_metadata
    if metadata_record is None:
        msg = f"video has no YouTube metadata: {record.youtube_video_id}"
        raise IncompleteVideoRecordError(msg)

    metadata = YouTubeMetadata(
        youtube_video_id=record.youtube_video_id,
        title=metadata_record.title,
        description=metadata_record.description,
        channel_id=metadata_record.channel_id,
        channel_title=metadata_record.channel_title,
        published_at=metadata_record.published_at,
        duration=_duration_from_seconds(metadata_record.duration_seconds),
        view_count=metadata_record.view_count,
        like_count=metadata_record.like_count,
        comment_count=metadata_record.comment_count,
        last_refreshed_at=metadata_record.last_refreshed_at,
        tags=tuple(metadata_record.tags or ()),
        thumbnail_url=metadata_record.thumbnail_url,
        video_url=metadata_record.video_url,
    )
    return Video(
        youtube_video_id=record.youtube_video_id,
        first_seen_at=record.first_seen_at,
        metadata=metadata,
    )


def _annotation_from_record(
    record: ResearchAnnotationRecord,
    youtube_video_id: str,
) -> ResearchAnnotation:
    return ResearchAnnotation(
        youtube_video_id=youtube_video_id,
        updated_at=record.updated_at,
        review_status=ReviewStatus(record.review_status),
        notes=record.notes,
        relevance_label=record.relevance_label,
        competition_name=record.competition_name,
        fencer_names=tuple(record.fencer_names or ()),
        weapon_category=record.weapon_category,
        event_notes=record.event_notes,
    )


def _update_annotation_record(
    record: ResearchAnnotationRecord,
    annotation: ResearchAnnotation,
) -> None:
    record.review_status = annotation.review_status.value
    record.notes = annotation.notes
    record.relevance_label = annotation.relevance_label
    record.competition_name = annotation.competition_name
    record.fencer_names = list(annotation.fencer_names)
    record.weapon_category = annotation.weapon_category
    record.event_notes = annotation.event_notes
    record.updated_at = annotation.updated_at


def _duration_seconds(duration: timedelta | None) -> int | None:
    if duration is None:
        return None
    return int(duration.total_seconds())


def _duration_from_seconds(duration_seconds: int | None) -> timedelta | None:
    if duration_seconds is None:
        return None
    return timedelta(seconds=duration_seconds)
