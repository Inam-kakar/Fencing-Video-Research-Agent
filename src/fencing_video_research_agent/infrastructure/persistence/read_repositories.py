"""SQLAlchemy read repositories for stored data inspection."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload, sessionmaker

from fencing_video_research_agent.infrastructure.persistence.models import (
    CollectionRunRecord,
    ResearchAnnotationRecord,
    SearchHitRecord,
    SearchQueryRecord,
    VideoRecord,
    YouTubeVideoMetadataRecord,
)
from fencing_video_research_agent.ports import CollectionRunRecordId, IncompleteVideoRecordError
from fencing_video_research_agent.ports.stored_data import (
    StoredCollectionRunDetail,
    StoredCollectionRunHit,
    StoredCollectionRunSummary,
    StoredDataSummary,
    StoredSearchHitTableRow,
    StoredVideoDetail,
    StoredVideoSummary,
    StoredVideoTableRow,
)


class SqlAlchemyStoredDataReader:
    """Read-only SQLAlchemy implementation for stored-video inspection."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def get_summary(self) -> StoredDataSummary:
        """Return dashboard-oriented counts for stored research data."""

        with self._session_factory() as session:
            video_count = _count_rows(session, VideoRecord)
            collection_run_count = _count_rows(session, CollectionRunRecord)
            search_hit_count = _count_rows(session, SearchHitRecord)
            annotation_count = _count_rows(session, ResearchAnnotationRecord)
            reviewed_count = (
                session.scalar(
                    select(func.count())
                    .select_from(ResearchAnnotationRecord)
                    .where(ResearchAnnotationRecord.review_status == "reviewed")
                )
                or 0
            )

        return StoredDataSummary(
            video_count=video_count,
            collection_run_count=collection_run_count,
            search_hit_count=search_hit_count,
            annotation_count=annotation_count,
            reviewed_count=reviewed_count,
            unreviewed_count=max(video_count - reviewed_count, 0),
        )

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

    def list_video_table_rows(
        self,
        *,
        limit: int,
        offset: int,
        search: str | None,
    ) -> tuple[StoredVideoTableRow, ...]:
        """Return stored videos shaped for the read-only API table."""

        with self._session_factory() as session:
            statement = (
                select(VideoRecord)
                .join(VideoRecord.youtube_metadata)
                .options(
                    joinedload(VideoRecord.youtube_metadata),
                    joinedload(VideoRecord.annotation),
                )
                .order_by(VideoRecord.first_seen_at.desc(), VideoRecord.youtube_video_id.asc())
                .offset(offset)
                .limit(limit)
            )
            if search is not None:
                pattern = f"%{search}%"
                statement = statement.where(
                    or_(
                        VideoRecord.youtube_video_id.ilike(pattern),
                        YouTubeVideoMetadataRecord.title.ilike(pattern),
                        YouTubeVideoMetadataRecord.channel_title.ilike(pattern),
                    )
                )
            records = session.scalars(statement).all()

        return tuple(_table_row_from_record(record) for record in records)

    def get_video(self, youtube_video_id: str) -> StoredVideoDetail | None:
        """Return one stored video detail by YouTube ID, if present."""

        with self._session_factory() as session:
            record = session.scalars(
                select(VideoRecord)
                .where(VideoRecord.youtube_video_id == youtube_video_id)
                .options(
                    joinedload(VideoRecord.youtube_metadata),
                    joinedload(VideoRecord.annotation),
                    selectinload(VideoRecord.search_hits)
                    .joinedload(SearchHitRecord.collection_run)
                    .joinedload(CollectionRunRecord.search_query),
                )
            ).one_or_none()
            if record is None:
                return None
            return _detail_from_record(record)

    def list_collection_runs(
        self,
        *,
        limit: int,
        offset: int = 0,
    ) -> tuple[StoredCollectionRunSummary, ...]:
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
                .offset(offset)
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

    def list_search_hit_table_rows(
        self,
        *,
        limit: int,
        offset: int,
        query_text: str | None,
    ) -> tuple[StoredSearchHitTableRow, ...]:
        """Return search-hit provenance rows shaped for the read-only API table."""

        with self._session_factory() as session:
            statement = (
                select(SearchHitRecord)
                .join(SearchHitRecord.collection_run)
                .join(CollectionRunRecord.search_query)
                .options(
                    joinedload(SearchHitRecord.collection_run).joinedload(
                        CollectionRunRecord.search_query
                    ),
                    joinedload(SearchHitRecord.video).joinedload(VideoRecord.youtube_metadata),
                    joinedload(SearchHitRecord.video).joinedload(VideoRecord.annotation),
                )
                .order_by(
                    CollectionRunRecord.started_at.desc(),
                    CollectionRunRecord.id.desc(),
                    SearchHitRecord.rank.asc(),
                    SearchHitRecord.id.asc(),
                )
                .offset(offset)
                .limit(limit)
            )
            if query_text is not None:
                statement = statement.where(SearchQueryRecord.query_text.ilike(f"%{query_text}%"))
            records = session.scalars(statement).all()

        return tuple(_search_hit_table_row_from_record(record) for record in records)


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
    provenance = _provenance_summary(record.search_hits)
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
        relevance_label=None if annotation is None else annotation.relevance_label,
        notes=None if annotation is None else annotation.notes,
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


def _table_row_from_record(record: VideoRecord) -> StoredVideoTableRow:
    metadata = _required_metadata(record)
    annotation = record.annotation
    return StoredVideoTableRow(
        youtube_video_id=record.youtube_video_id,
        title=metadata.title,
        channel_title=metadata.channel_title,
        duration_seconds=metadata.duration_seconds,
        published_at=metadata.published_at,
        view_count=metadata.view_count,
        review_status=None if annotation is None else annotation.review_status,
        relevance_label=None if annotation is None else annotation.relevance_label,
        video_url=metadata.video_url,
        first_seen_at=record.first_seen_at,
        last_refreshed_at=metadata.last_refreshed_at,
    )


def _hit_from_record(record: SearchHitRecord) -> StoredCollectionRunHit:
    metadata = _required_metadata(record.video)
    return StoredCollectionRunHit(
        rank=record.rank,
        youtube_video_id=record.video.youtube_video_id,
        title=metadata.title,
        channel_title=metadata.channel_title,
    )


def _search_hit_table_row_from_record(record: SearchHitRecord) -> StoredSearchHitTableRow:
    metadata = _required_metadata(record.video)
    annotation = record.video.annotation
    return StoredSearchHitTableRow(
        collection_run_id=CollectionRunRecordId(record.collection_run.id),
        query_text=record.collection_run.search_query.query_text,
        run_started_at=record.collection_run.started_at,
        rank=record.rank,
        discovered_at=record.discovered_at,
        youtube_video_id=record.video.youtube_video_id,
        title=metadata.title,
        channel_title=metadata.channel_title,
        review_status=None if annotation is None else annotation.review_status,
        relevance_label=None if annotation is None else annotation.relevance_label,
    )


def _required_metadata(record: VideoRecord) -> YouTubeVideoMetadataRecord:
    metadata = record.youtube_metadata
    if metadata is None:
        msg = f"video has no YouTube metadata: {record.youtube_video_id}"
        raise IncompleteVideoRecordError(msg)
    return metadata


def _count_rows(session: Session, model: type[object]) -> int:
    return session.scalar(select(func.count()).select_from(model)) or 0


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
