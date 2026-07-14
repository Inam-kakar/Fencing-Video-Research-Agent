"""Tests for infrastructure settings."""

from __future__ import annotations

import pytest

from fencing_video_research_agent.infrastructure.settings import (
    ConfigurationError,
    load_settings,
)


def test_settings_load_youtube_api_key_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("YOUTUBE_API_KEY", "test-api-key")

    settings = load_settings(env_file=None)

    assert settings.youtube_api_key.get_secret_value() == "test-api-key"
    assert settings.database_url == "sqlite:///data/fencing_video_research.db"
    assert settings.log_level == "INFO"


def test_missing_youtube_api_key_raises_sanitized_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)

    with pytest.raises(ConfigurationError) as error:
        load_settings(env_file=None)

    assert "YOUTUBE_API_KEY" in str(error.value)
    assert "api-key" not in str(error.value).lower()


def test_read_only_settings_do_not_require_youtube_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///tmp/read-only.sqlite")

    settings = load_settings(env_file=None, require_youtube_api_key=False)

    assert settings.youtube_api_key.get_secret_value() == ""
    assert settings.database_url == "sqlite:///tmp/read-only.sqlite"


def test_secret_string_representation_does_not_expose_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("YOUTUBE_API_KEY", "super-secret-key")

    settings = load_settings(env_file=None)

    assert "super-secret-key" not in str(settings.youtube_api_key)
    assert "super-secret-key" not in repr(settings)


def test_settings_load_database_url_and_log_level(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("YOUTUBE_API_KEY", "test-api-key")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///tmp/research.sqlite")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    settings = load_settings(env_file=None)

    assert settings.database_url == "sqlite:///tmp/research.sqlite"
    assert settings.log_level == "DEBUG"
