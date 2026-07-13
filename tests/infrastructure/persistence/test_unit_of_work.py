"""Tests for SQLAlchemy Unit of Work transaction behavior."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from fencing_video_research_agent.domain import Video, YouTubeMetadata
from fencing_video_research_agent.infrastructure.persistence.models import VideoRecord
from fencing_video_research_agent.infrastructure.persistence.unit_of_work import (
    SqlAlchemyUnitOfWork,
)

NOW = datetime(2026, 7, 13, 9, 0, tzinfo=UTC)


def make_video(youtube_video_id: str = "video-123") -> Video:
    """Create a valid video for Unit of Work tests."""

    return Video(
        youtube_video_id=youtube_video_id,
        first_seen_at=NOW,
        metadata=YouTubeMetadata(
            youtube_video_id=youtube_video_id,
            title="Sabre semifinal",
            description=None,
            channel_id="channel-123",
            channel_title="Fencing Channel",
            published_at=NOW - timedelta(days=1),
            duration=timedelta(minutes=8),
            view_count=None,
            like_count=None,
            comment_count=None,
            last_refreshed_at=NOW,
        ),
    )


def video_count(session_factory: sessionmaker[Session]) -> int:
    """Return the number of stored videos."""

    with session_factory() as session:
        return session.scalar(select(func.count()).select_from(VideoRecord)) or 0


def test_unit_of_work_commit_persists_changes(
    session_factory: sessionmaker[Session],
) -> None:
    """Changes are persisted only when commit is explicitly called."""

    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        unit_of_work.videos.add_or_update(make_video())
        unit_of_work.commit()

    assert video_count(session_factory) == 1


def test_unit_of_work_rolls_back_without_commit(
    session_factory: sessionmaker[Session],
) -> None:
    """Exiting without commit discards pending changes."""

    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        unit_of_work.videos.add_or_update(make_video())

    assert video_count(session_factory) == 0


def test_unit_of_work_rolls_back_on_exception(
    session_factory: sessionmaker[Session],
) -> None:
    """Exceptions roll back pending changes before the session closes."""

    with pytest.raises(RuntimeError, match="stop"):
        with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
            unit_of_work.videos.add_or_update(make_video())
            raise RuntimeError("stop")

    assert video_count(session_factory) == 0


def test_unit_of_work_explicit_rollback_discards_changes(
    session_factory: sessionmaker[Session],
) -> None:
    """Explicit rollback clears pending changes inside the active Unit of Work."""

    with SqlAlchemyUnitOfWork(session_factory) as unit_of_work:
        unit_of_work.videos.add_or_update(make_video())
        unit_of_work.rollback()
        unit_of_work.commit()

    assert video_count(session_factory) == 0


def test_unit_of_work_repositories_require_active_context(
    session_factory: sessionmaker[Session],
) -> None:
    """Repositories are only available while the Unit of Work is active."""

    unit_of_work = SqlAlchemyUnitOfWork(session_factory)

    with pytest.raises(RuntimeError, match="not active"):
        _ = unit_of_work.videos
