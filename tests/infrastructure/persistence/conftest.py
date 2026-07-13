"""Shared Alembic-backed persistence test fixtures."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from fencing_video_research_agent.infrastructure.persistence.database import (
    create_database_engine,
    create_session_factory,
)


def sqlite_url(database_path: Path) -> str:
    """Return a SQLAlchemy SQLite URL for a temporary database path."""

    return f"sqlite:///{database_path.as_posix()}"


def make_alembic_config(database_path: Path) -> Config:
    """Create Alembic config with a test-specific database URL."""

    config = Config("alembic.ini")
    config.set_main_option("script_location", "alembic")
    config.set_main_option("sqlalchemy.url", sqlite_url(database_path))
    return config


@pytest.fixture
def migrated_engine(tmp_path: Path) -> Iterator[Engine]:
    """Run Alembic migrations against a temporary SQLite database."""

    database_path = tmp_path / "phase1.sqlite"
    command.upgrade(make_alembic_config(database_path), "head")
    engine = create_database_engine(sqlite_url(database_path))
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def session_factory(migrated_engine: Engine) -> sessionmaker[Session]:
    """Return a session factory bound to an Alembic-migrated test database."""

    return create_session_factory(migrated_engine)
