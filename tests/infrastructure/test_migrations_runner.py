"""Tests for runtime Alembic migration helpers."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import inspect

from fencing_video_research_agent.infrastructure.migrations import ensure_database_current
from fencing_video_research_agent.infrastructure.persistence.database import create_database_engine


def sqlite_url(database_path: Path) -> str:
    """Return a SQLite URL for a temporary database path."""

    return f"sqlite:///{database_path.as_posix()}"


def test_ensure_database_current_runs_alembic_upgrade_on_temporary_sqlite(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "nested" / "research.sqlite"
    database_url = sqlite_url(database_path)

    ensure_database_current(database_url)

    engine = create_database_engine(database_url)
    try:
        tables = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()

    assert database_path.exists()
    assert {"videos", "search_queries", "collection_runs", "search_hits"}.issubset(tables)
