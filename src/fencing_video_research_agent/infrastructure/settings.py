"""Centralized infrastructure settings for the research application."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from pydantic import Field, SecretStr, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfigurationError(Exception):
    """Raised when required application configuration is missing or invalid."""


class AppSettings(BaseSettings):
    """Runtime settings loaded from environment variables or a local env file."""

    model_config = SettingsConfigDict(
        env_prefix="",
        extra="ignore",
    )

    youtube_api_key: SecretStr = Field(
        default=SecretStr(""),
        validation_alias="YOUTUBE_API_KEY",
    )
    database_url: str = Field(
        default="sqlite:///data/fencing_video_research.db",
        validation_alias="DATABASE_URL",
    )
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")


def load_settings(
    *,
    env_file: str | Path | None = ".env",
    require_youtube_api_key: bool = True,
) -> AppSettings:
    """Load settings, raising a sanitized error for missing required values."""

    try:
        settings_factory = cast(Any, AppSettings)
        settings = cast(AppSettings, settings_factory(_env_file=env_file))
    except ValidationError as exc:
        raise _configuration_error() from exc

    if require_youtube_api_key and not settings.youtube_api_key.get_secret_value().strip():
        raise _configuration_error()
    if not settings.database_url.strip():
        raise ConfigurationError("Missing or invalid configuration: DATABASE_URL is required")
    if not settings.log_level.strip():
        raise ConfigurationError("Missing or invalid configuration: LOG_LEVEL is required")

    return settings


def _configuration_error() -> ConfigurationError:
    return ConfigurationError("Missing or invalid configuration: YOUTUBE_API_KEY is required")
