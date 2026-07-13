"""Alembic migration helpers for runtime database initialization."""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy.engine import make_url


class MigrationError(Exception):
    """Raised when runtime database migration fails."""


def ensure_database_current(
    database_url: str,
    *,
    config_path: str | Path = "alembic.ini",
) -> None:
    """Run Alembic upgrade to head for the configured database URL."""

    if not database_url.strip():
        msg = "Database migration failed"
        raise MigrationError(msg)

    _ensure_sqlite_parent_directory(database_url)
    config = Config(str(config_path))
    config.set_main_option("script_location", "alembic")
    config.set_main_option("sqlalchemy.url", database_url)

    try:
        command.upgrade(config, "head")
    except Exception as exc:
        msg = "Database migration failed"
        raise MigrationError(msg) from exc


def _ensure_sqlite_parent_directory(database_url: str) -> None:
    url = make_url(database_url)
    if url.get_backend_name() != "sqlite" or not url.database or url.database == ":memory:":
        return

    database_path = Path(url.database)
    parent = database_path.parent
    if parent != Path("."):
        parent.mkdir(parents=True, exist_ok=True)
