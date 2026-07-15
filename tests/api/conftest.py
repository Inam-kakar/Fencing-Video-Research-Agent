"""Shared fixtures for read-only FastAPI endpoint tests."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from fencing_video_research_agent.api.main import create_app
from fencing_video_research_agent.domain import (
    CollectionRun,
    ResearchAnnotation,
    ReviewStatus,
    SearchQuery,
    Video,
    YouTubeMetadata,
)
from fencing_video_research_agent.infrastructure.migrations import ensure_database_current
from fencing_video_research_agent.infrastructure.persistence.database import (
    create_database_engine,
    create_session_factory,
)
from fencing_video_research_agent.infrastructure.persistence.repositories import (
    SqlAlchemyAnnotationRepository,
    SqlAlchemyCollectionRepository,
    SqlAlchemyVideoRepository,
)
from fencing_video_research_agent.infrastructure.settings import AppSettings

NOW = datetime(2026, 7, 15, 9, 0, tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class ApiDatabase:
    """Temporary API database resources."""

    database_url: str
    engine: Engine
    session_factory: sessionmaker[Session]


@pytest.fixture
def api_database(tmp_path: Path) -> Iterator[ApiDatabase]:
    """Create an Alembic-migrated temporary SQLite database for API tests."""

    database_path = tmp_path / "api.sqlite"
    database_url = f"sqlite:///{database_path.as_posix()}"
    ensure_database_current(database_url)
    engine = create_database_engine(database_url)
    session_factory = create_session_factory(engine)
    try:
        yield ApiDatabase(
            database_url=database_url,
            engine=engine,
            session_factory=session_factory,
        )
    finally:
        engine.dispose()


@pytest.fixture
def api_client(api_database: ApiDatabase) -> Iterator[TestClient]:
    """Create a TestClient for the read-only API app."""

    settings = AppSettings.model_construct(
        youtube_api_key=SecretStr(""),
        database_url=api_database.database_url,
        log_level="INFO",
    )
    app = create_app(settings=settings)
    with TestClient(app) as client:
        yield client


def make_video(
    youtube_video_id: str = "video-123",
    *,
    title: str = "Sabre final",
    first_seen_at: datetime = NOW,
) -> Video:
    """Create a domain video for API tests."""

    return Video(
        youtube_video_id=youtube_video_id,
        first_seen_at=first_seen_at,
        metadata=YouTubeMetadata(
            youtube_video_id=youtube_video_id,
            title=title,
            description="A public sabre fencing bout.",
            channel_id="channel-123",
            channel_title="Fencing Channel",
            published_at=first_seen_at - timedelta(days=1),
            duration=timedelta(minutes=12),
            view_count=100,
            like_count=10,
            comment_count=5,
            tags=("sabre", "final"),
            thumbnail_url="https://example.test/thumb.jpg",
            video_url=f"https://www.youtube.com/watch?v={youtube_video_id}",
            last_refreshed_at=first_seen_at + timedelta(minutes=5),
        ),
    )


def seed_video(
    session_factory: sessionmaker[Session],
    youtube_video_id: str = "video-123",
    *,
    title: str = "Sabre final",
    first_seen_at: datetime = NOW,
) -> None:
    """Store one video through the SQLAlchemy repository."""

    with session_factory() as session:
        SqlAlchemyVideoRepository(session).add_or_update(
            make_video(
                youtube_video_id=youtube_video_id,
                title=title,
                first_seen_at=first_seen_at,
            )
        )
        session.commit()


def seed_annotation(
    session_factory: sessionmaker[Session],
    youtube_video_id: str = "video-123",
    *,
    review_status: ReviewStatus = ReviewStatus.REVIEWED,
    relevance_label: str | None = "relevant",
) -> None:
    """Store one annotation through the SQLAlchemy repository."""

    with session_factory() as session:
        SqlAlchemyAnnotationRepository(session).save(
            ResearchAnnotation(
                youtube_video_id=youtube_video_id,
                updated_at=NOW + timedelta(minutes=10),
                review_status=review_status,
                notes="Useful reference.",
                relevance_label=relevance_label,
                competition_name="European Championship",
                fencer_names=("Fencer One", "Fencer Two"),
                weapon_category="sabre",
                event_notes="Final bout",
            )
        )
        session.commit()


def seed_collection_run(
    session_factory: sessionmaker[Session],
    *,
    query_text: str = "sabre fencing final",
    youtube_video_id: str = "video-123",
    rank: int | None = 1,
) -> int:
    """Store one collection run and search hit through SQLAlchemy repositories."""

    with session_factory() as session:
        collections = SqlAlchemyCollectionRepository(session)
        run_id = collections.add_collection_run(
            CollectionRun(
                search_query=SearchQuery(query_text, parameters={"max_results": 5}),
                started_at=NOW,
                completed_at=NOW + timedelta(minutes=1),
            ),
            status="completed",
        )
        collections.add_search_hit(
            run_id,
            youtube_video_id=youtube_video_id,
            discovered_at=NOW + timedelta(seconds=30),
            rank=rank,
        )
        session.commit()
        return int(run_id)
