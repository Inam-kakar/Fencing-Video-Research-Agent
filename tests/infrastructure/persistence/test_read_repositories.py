"""Tests for SQLAlchemy read repositories."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session, sessionmaker
from tests.infrastructure.persistence.test_repositories import make_metadata

from fencing_video_research_agent.domain import ResearchAnnotation, ReviewStatus, Video
from fencing_video_research_agent.infrastructure.persistence.read_repositories import (
    SqlAlchemyStoredDataReader,
)
from fencing_video_research_agent.infrastructure.persistence.repositories import (
    SqlAlchemyAnnotationRepository,
    SqlAlchemyVideoRepository,
)

NOW = datetime(2026, 7, 13, 8, 0, tzinfo=UTC)


def make_video(
    youtube_video_id: str,
    *,
    first_seen_at: datetime,
    title: str,
) -> Video:
    """Create a domain video for read-repository tests."""

    return Video(
        youtube_video_id=youtube_video_id,
        first_seen_at=first_seen_at,
        metadata=make_metadata(
            youtube_video_id=youtube_video_id,
            title=title,
            last_refreshed_at=first_seen_at + timedelta(minutes=5),
        ),
    )


def test_reader_lists_videos_newest_first(
    session_factory: sessionmaker[Session],
) -> None:
    """Video summaries are ordered by first-seen time, then YouTube ID."""

    with session_factory() as session:
        videos = SqlAlchemyVideoRepository(session)
        videos.add_or_update(
            make_video("video-b", first_seen_at=NOW + timedelta(hours=1), title="Newer B")
        )
        videos.add_or_update(
            make_video("video-a", first_seen_at=NOW + timedelta(hours=1), title="Newer A")
        )
        videos.add_or_update(make_video("video-c", first_seen_at=NOW, title="Older C"))
        session.commit()

    reader = SqlAlchemyStoredDataReader(session_factory)

    summaries = reader.list_videos(limit=10)

    assert [summary.youtube_video_id for summary in summaries] == [
        "video-a",
        "video-b",
        "video-c",
    ]
    assert summaries[0].title == "Newer A"
    assert summaries[0].last_refreshed_at == NOW + timedelta(hours=1, minutes=5)


def test_reader_respects_list_limit(session_factory: sessionmaker[Session]) -> None:
    """The read repository applies the caller-provided list limit."""

    with session_factory() as session:
        videos = SqlAlchemyVideoRepository(session)
        videos.add_or_update(make_video("video-1", first_seen_at=NOW, title="One"))
        videos.add_or_update(make_video("video-2", first_seen_at=NOW, title="Two"))
        session.commit()

    reader = SqlAlchemyStoredDataReader(session_factory)

    summaries = reader.list_videos(limit=1)

    assert len(summaries) == 1


def test_reader_returns_empty_tuple_for_empty_database(
    session_factory: sessionmaker[Session],
) -> None:
    """An empty migrated database produces an empty read result."""

    reader = SqlAlchemyStoredDataReader(session_factory)

    assert reader.list_videos(limit=20) == ()


def test_reader_returns_video_detail_with_annotation_status(
    session_factory: sessionmaker[Session],
) -> None:
    """Video detail includes YouTube metadata and separate annotation status."""

    with session_factory() as session:
        SqlAlchemyVideoRepository(session).add_or_update(
            make_video("video-123", first_seen_at=NOW, title="Sabre final")
        )
        SqlAlchemyAnnotationRepository(session).save(
            ResearchAnnotation(
                youtube_video_id="video-123",
                updated_at=NOW,
                review_status=ReviewStatus.REVIEWED,
                notes="Useful reference.",
            )
        )
        session.commit()

    reader = SqlAlchemyStoredDataReader(session_factory)

    detail = reader.get_video("video-123")

    assert detail is not None
    assert detail.youtube_video_id == "video-123"
    assert detail.title == "Sabre final"
    assert detail.channel_id == "channel-123"
    assert detail.duration_seconds == 720
    assert detail.tags == ("sabre", "final")
    assert detail.annotation_status == "reviewed"


def test_reader_returns_none_for_missing_video(
    session_factory: sessionmaker[Session],
) -> None:
    """Missing videos are represented without raising from the reader."""

    reader = SqlAlchemyStoredDataReader(session_factory)

    assert reader.get_video("missing-video") is None
