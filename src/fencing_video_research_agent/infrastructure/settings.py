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

    youtube_api_key: SecretStr = Field(validation_alias="YOUTUBE_API_KEY")


def load_settings(*, env_file: str | Path | None = ".env") -> AppSettings:
    """Load settings, raising a sanitized error for missing required values."""

    try:
        settings_factory = cast(Any, AppSettings)
        settings = cast(AppSettings, settings_factory(_env_file=env_file))
    except ValidationError as exc:
        raise _configuration_error() from exc

    if not settings.youtube_api_key.get_secret_value().strip():
        raise _configuration_error()

    return settings


def _configuration_error() -> ConfigurationError:
    return ConfigurationError("Missing or invalid configuration: YOUTUBE_API_KEY is required")
