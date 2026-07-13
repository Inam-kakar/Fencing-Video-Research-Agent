"""Migration tests for the Phase 1 persistence schema."""

from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import StatementError
from sqlalchemy.orm import Session

from fencing_video_research_agent.infrastructure.persistence.database import (
    create_database_engine,
)
from fencing_video_research_agent.infrastructure.persistence.models import (
    CollectionRunRecord,
    ResearchAnnotationRecord,
    SearchHitRecord,
    SearchQueryRecord,
    VideoRecord,
    YouTubeVideoMetadataRecord,
)

EXPECTED_TABLES = {
    "collection_runs",
    "research_annotations",
    "search_hits",
    "search_queries",
    "videos",
    "youtube_video_metadata",
}


def sqlite_url(database_path: Path) -> str:
    """Return a SQLAlchemy SQLite URL for a temporary database path."""

    return f"sqlite:///{database_path.as_posix()}"


def make_alembic_config(database_path: Path) -> Config:
    """Create Alembic config with a test-specific database URL."""

    config = Config("alembic.ini")
    config.set_main_option("script_location", "alembic")
    config.set_main_option("sqlalchemy.url", sqlite_url(database_path))
    return config


def upgrade_database(database_path: Path) -> Engine:
    """Run Alembic upgrade against a temporary SQLite database."""

    command.upgrade(make_alembic_config(database_path), "head")
    return create_database_engine(sqlite_url(database_path))


def unique_column_sets(inspector: Any, table_name: str) -> set[tuple[str, ...]]:
    """Return unique constraint column sets for a reflected table."""

    return {
        tuple(constraint["column_names"])
        for constraint in inspector.get_unique_constraints(table_name)
    }


def index_names(inspector: Any, table_name: str) -> set[str]:
    """Return reflected index names for a table."""

    return {index["name"] for index in inspector.get_indexes(table_name)}


def foreign_key_targets(inspector: Any, table_name: str) -> set[tuple[tuple[str, ...], str]]:
    """Return constrained columns and referred table names for table foreign keys."""

    return {
        (tuple(foreign_key["constrained_columns"]), foreign_key["referred_table"])
        for foreign_key in inspector.get_foreign_keys(table_name)
    }


def test_alembic_upgrade_creates_phase1_schema(tmp_path: Path) -> None:
    """Alembic creates the expected Phase 1 tables, constraints, and indexes."""

    engine = upgrade_database(tmp_path / "phase1.sqlite")
    try:
        inspector = inspect(engine)

        assert EXPECTED_TABLES <= set(inspector.get_table_names())
        assert "search_query_id" not in {
            column["name"] for column in inspector.get_columns("search_hits")
        }

        assert ("youtube_video_id",) in unique_column_sets(inspector, "videos")
        assert ("video_id",) in unique_column_sets(inspector, "youtube_video_metadata")
        assert ("query_text", "parameters_fingerprint") in unique_column_sets(
            inspector,
            "search_queries",
        )
        assert ("collection_run_id", "video_id") in unique_column_sets(
            inspector,
            "search_hits",
        )
        assert ("video_id",) in unique_column_sets(inspector, "research_annotations")

        assert (
            ("search_query_id",),
            "search_queries",
        ) in foreign_key_targets(inspector, "collection_runs")
        assert (
            ("collection_run_id",),
            "collection_runs",
        ) in foreign_key_targets(inspector, "search_hits")
        assert (("video_id",), "videos") in foreign_key_targets(inspector, "search_hits")

        assert "ix_videos_youtube_video_id" in index_names(inspector, "videos")
        assert "ix_collection_runs_search_query_id" in index_names(
            inspector,
            "collection_runs",
        )
        assert "ix_search_hits_video_id" in index_names(inspector, "search_hits")
        assert "ix_research_annotations_review_status" in index_names(
            inspector,
            "research_annotations",
        )
    finally:
        engine.dispose()


def test_alembic_downgrade_to_base_removes_phase1_schema(tmp_path: Path) -> None:
    """Alembic downgrade removes the Phase 1 application tables."""

    database_path = tmp_path / "phase1.sqlite"
    config = make_alembic_config(database_path)
    command.upgrade(config, "head")
    command.downgrade(config, "base")

    engine = create_database_engine(sqlite_url(database_path))
    try:
        table_names = set(inspect(engine).get_table_names())
        assert EXPECTED_TABLES.isdisjoint(table_names)
    finally:
        engine.dispose()


def test_utc_datetimes_round_trip_through_sqlite(tmp_path: Path) -> None:
    """UTCDateTime normalizes aware values and returns timezone-aware UTC values."""

    engine = upgrade_database(tmp_path / "phase1.sqlite")
    offset_time = datetime(2026, 7, 13, 12, 30, tzinfo=timezone(timedelta(hours=2)))
    utc_time = offset_time.astimezone(UTC)

    try:
        with Session(engine) as session:
            video = VideoRecord(youtube_video_id="video-123", first_seen_at=offset_time)
            video.youtube_metadata = YouTubeVideoMetadataRecord(
                title="Sabre final",
                description=None,
                channel_id="channel-123",
                channel_title="Fencing Channel",
                published_at=offset_time,
                duration_seconds=720,
                view_count=None,
                like_count=None,
                comment_count=None,
                thumbnail_url=None,
                video_url="https://www.youtube.com/watch?v=video-123",
                last_refreshed_at=offset_time,
            )
            search_query = SearchQueryRecord(
                query_text="sabre fencing",
                parameters_fingerprint="44136fa355b3678a1146ad16f7e8649e",
                created_at=offset_time,
            )
            collection_run = CollectionRunRecord(
                search_query=search_query,
                started_at=offset_time,
                completed_at=offset_time,
                status="completed",
                error_message=None,
            )
            search_hit = SearchHitRecord(
                collection_run=collection_run,
                video=video,
                discovered_at=offset_time,
                rank=1,
            )
            annotation = ResearchAnnotationRecord(
                video=video,
                review_status="unreviewed",
                updated_at=offset_time,
            )
            session.add_all([video, search_query, search_hit, annotation])
            session.commit()
            session.expunge_all()

            stored_video = session.scalars(
                select(VideoRecord).where(VideoRecord.youtube_video_id == "video-123")
            ).one()
            stored_query = session.scalars(select(SearchQueryRecord)).one()

            assert stored_video.first_seen_at == utc_time
            assert stored_video.first_seen_at.tzinfo is UTC
            assert stored_video.youtube_metadata is not None
            assert stored_video.youtube_metadata.last_refreshed_at == utc_time
            assert stored_video.youtube_metadata.tags == []
            assert stored_query.parameters == {}
            assert stored_video.annotation is not None
            assert stored_video.annotation.fencer_names == []
    finally:
        engine.dispose()


def test_utc_datetime_rejects_naive_values(tmp_path: Path) -> None:
    """UTCDateTime rejects naive datetimes before they reach SQLite."""

    engine = upgrade_database(tmp_path / "phase1.sqlite")
    try:
        with Session(engine) as session:
            session.add(
                VideoRecord(
                    youtube_video_id="video-naive",
                    first_seen_at=datetime(2026, 7, 13, 12, 30),
                )
            )

            with pytest.raises(StatementError, match="timezone-aware"):
                session.flush()
    finally:
        engine.dispose()
