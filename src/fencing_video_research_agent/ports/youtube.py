"""Project-owned YouTube gateway contracts.

The concrete adapter will translate official YouTube Data API responses into these
types before the application layer sees them.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from types import MappingProxyType
from typing import Protocol

from fencing_video_research_agent.domain.models import (
    SearchParameterValue,
    YouTubeMetadata,
)


def _require_non_empty(name: str, value: str) -> str:
    stripped = value.strip()
    if not stripped:
        msg = f"{name} must not be empty"
        raise ValueError(msg)
    return stripped


def _require_optional_utc(name: str, value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        msg = f"{name} must be timezone-aware and UTC"
        raise ValueError(msg)
    return value


@dataclass(frozen=True, slots=True)
class YouTubeSearchRequest:
    """A project-owned request for YouTube video discovery."""

    query_text: str
    max_results: int
    parameters: Mapping[str, SearchParameterValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "query_text",
            _require_non_empty("query_text", self.query_text),
        )
        if self.max_results < 1:
            msg = "max_results must be positive"
            raise ValueError(msg)
        object.__setattr__(self, "parameters", MappingProxyType(dict(self.parameters)))


@dataclass(frozen=True, slots=True)
class YouTubeSearchResult:
    """One video returned by YouTube search before full metadata enrichment."""

    youtube_video_id: str
    rank: int | None = None
    title: str | None = None
    channel_id: str | None = None
    channel_title: str | None = None
    published_at: datetime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "youtube_video_id",
            _require_non_empty("youtube_video_id", self.youtube_video_id),
        )
        object.__setattr__(
            self,
            "published_at",
            _require_optional_utc("published_at", self.published_at),
        )
        if self.rank is not None and self.rank < 1:
            msg = "rank must be positive when provided"
            raise ValueError(msg)


class YouTubeGatewayError(Exception):
    """Base error for YouTube gateway failures."""


class TransientYouTubeGatewayError(YouTubeGatewayError):
    """Retryable YouTube gateway failure such as rate limiting or service unavailability."""


class PermanentYouTubeGatewayError(YouTubeGatewayError):
    """Non-retryable YouTube gateway failure such as invalid request parameters."""


class YouTubeGateway(Protocol):
    """Boundary for official YouTube Data API discovery and metadata enrichment."""

    def search_videos(self, request: YouTubeSearchRequest) -> tuple[YouTubeSearchResult, ...]:
        """Search for public videos and return project-owned search results."""

    def fetch_video_metadata(self, video_ids: Sequence[str]) -> tuple[YouTubeMetadata, ...]:
        """Fetch project-owned metadata for the given YouTube video IDs."""
