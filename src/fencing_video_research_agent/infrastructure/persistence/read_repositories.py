"""SQLAlchemy read repositories for stored data inspection."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, sessionmaker

from fencing_video_research_agent.infrastructure.persistence.models import (
    VideoRecord,
    YouTubeVideoMetadataRecord,
)
from fencing_video_research_agent.ports import (
    IncompleteVideoRecordError,
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


def _required_metadata(record: VideoRecord) -> YouTubeVideoMetadataRecord:
    metadata = record.youtube_metadata
    if metadata is None:
        msg = f"video has no YouTube metadata: {record.youtube_video_id}"
        raise IncompleteVideoRecordError(msg)
    return metadata
