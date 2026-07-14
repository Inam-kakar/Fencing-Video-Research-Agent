"""SQLAlchemy read repositories for stored data inspection."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload, sessionmaker

from fencing_video_research_agent.infrastructure.persistence.models import (
    CollectionRunRecord,
    SearchHitRecord,
    SearchQueryRecord,
    VideoRecord,
    YouTubeVideoMetadataRecord,
)
from fencing_video_research_agent.ports import (
    CollectionRunRecordId,
    IncompleteVideoRecordError,
    StoredCollectionRunDetail,
    StoredCollectionRunHit,
    StoredCollectionRunSummary,
    StoredVideoDetail,
    StoredVideoSummary,
)


class SqlAlchemyStoredDataReader:
    """Read-only SQLAlchemy implementation for stored-video inspection."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def list_videos(self, *, limit: int) -> tuple[StoredVideoSummary, ...]:
        """Return stored videos ordered newest first by first-seen timestamp."""

        with self._session_factory() as session:
            records = session.scalars(
                select(VideoRecord)
                .options(joinedload(VideoRecord.youtube_metadata))
                .order_by(VideoRecord.first_seen_at.desc(), VideoRecord.youtube_video_id.asc())
                .limit(limit)
            ).all()
            return tuple(_summary_from_record(record) for record in records)

    def get_video(self, youtube_video_id: str) -> StoredVideoDetail | None:
        """Return one stored video detail by YouTube ID, if present."""

        with self._session_factory() as session:
            record = session.scalars(
                select(VideoRecord)
                .where(VideoRecord.youtube_video_id == youtube_video_id)
                .options(
                    joinedload(VideoRecord.youtube_metadata),
                    joinedload(VideoRecord.annotation),
                )
            ).one_or_none()
            if record is None:
                return None
            return _detail_from_record(record)

    def list_collection_runs(self, *, limit: int) -> tuple[StoredCollectionRunSummary, ...]:
        """Return collection runs ordered newest first by started timestamp."""

        with self._session_factory() as session:
            rows = session.execute(
                select(
                    CollectionRunRecord.id,
                    SearchQueryRecord.query_text,
                    CollectionRunRecord.status,
                    CollectionRunRecord.started_at,
                    CollectionRunRecord.completed_at,
                    func.count(SearchHitRecord.id),
                )
                .join(
                    SearchQueryRecord,
                    CollectionRunRecord.search_query_id == SearchQueryRecord.id,
                )
                .outerjoin(
                    SearchHitRecord,
                    SearchHitRecord.collection_run_id == CollectionRunRecord.id,
                )
                .group_by(
                    CollectionRunRecord.id,
                    SearchQueryRecord.query_text,
                    CollectionRunRecord.status,
                    CollectionRunRecord.started_at,
                    CollectionRunRecord.completed_at,
                )
                .order_by(CollectionRunRecord.started_at.desc(), CollectionRunRecord.id.desc())
                .limit(limit)
            ).all()

        return tuple(
            StoredCollectionRunSummary(
                run_id=CollectionRunRecordId(row[0]),
                query_text=row[1],
                status=row[2],
                started_at=row[3],
                completed_at=row[4],
                hit_count=row[5],
            )
            for row in rows
        )

    def get_collection_run(
        self,
        run_id: CollectionRunRecordId,
    ) -> StoredCollectionRunDetail | None:
        """Return one collection run with returned videos, if present."""

        with self._session_factory() as session:
            record = session.scalars(
                select(CollectionRunRecord)
                .where(CollectionRunRecord.id == int(run_id))
                .options(
                    joinedload(CollectionRunRecord.search_query),
                    selectinload(CollectionRunRecord.search_hits)
                    .joinedload(SearchHitRecord.video)
                    .joinedload(VideoRecord.youtube_metadata),
                )
            ).one_or_none()
            if record is None:
                return None

            hits = tuple(
                _hit_from_record(hit)
                for hit in sorted(
                    record.search_hits,
                    key=lambda hit: (
                        hit.rank is None,
                        hit.rank or 0,
                        hit.video.youtube_video_id,
                    ),
                )
            )
            return StoredCollectionRunDetail(
                run_id=CollectionRunRecordId(record.id),
                query_text=record.search_query.query_text,
                query_parameters=record.search_query.parameters,
                status=record.status,
                started_at=record.started_at,
                completed_at=record.completed_at,
                hit_count=len(hits),
                hits=hits,
            )


def _summary_from_record(record: VideoRecord) -> StoredVideoSummary:
    metadata = _required_metadata(record)
    return StoredVideoSummary(
        youtube_video_id=record.youtube_video_id,
        title=metadata.title,
        channel_title=metadata.channel_title,
        published_at=metadata.published_at,
        first_seen_at=record.first_seen_at,
        last_refreshed_at=metadata.last_refreshed_at,
    )


def _detail_from_record(record: VideoRecord) -> StoredVideoDetail:
    metadata = _required_metadata(record)
    annotation = record.annotation
    return StoredVideoDetail(
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
        annotation_status=None if annotation is None else annotation.review_status,
    )


def _hit_from_record(record: SearchHitRecord) -> StoredCollectionRunHit:
    metadata = _required_metadata(record.video)
    return StoredCollectionRunHit(
        rank=record.rank,
        youtube_video_id=record.video.youtube_video_id,
        title=metadata.title,
        channel_title=metadata.channel_title,
    )


def _required_metadata(record: VideoRecord) -> YouTubeVideoMetadataRecord:
    metadata = record.youtube_metadata
    if metadata is None:
        msg = f"video has no YouTube metadata: {record.youtube_video_id}"
        raise IncompleteVideoRecordError(msg)
    return metadata
