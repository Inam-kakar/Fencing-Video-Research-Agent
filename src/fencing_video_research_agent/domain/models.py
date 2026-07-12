"""Framework-free domain models for Phase 1 metadata research."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from types import MappingProxyType

from fencing_video_research_agent.domain.enums import ReviewStatus

type SearchParameterValue = str | int | bool | None


def _require_non_empty(name: str, value: str) -> str:
    stripped = value.strip()
    if not stripped:
        msg = f"{name} must not be empty"
        raise ValueError(msg)
    return stripped


def _require_utc(name: str, value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        msg = f"{name} must be timezone-aware and UTC"
        raise ValueError(msg)
    return value


def _require_optional_utc(name: str, value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return _require_utc(name, value)


def _require_non_negative(name: str, value: int | None) -> int | None:
    if value is not None and value < 0:
        msg = f"{name} must be non-negative when provided"
        raise ValueError(msg)
    return value


@dataclass(frozen=True, slots=True)
class YouTubeMetadata:
    """Latest project-owned YouTube metadata for a video."""

    youtube_video_id: str
    title: str
    description: str | None
    channel_id: str
    channel_title: str
    published_at: datetime | None
    duration: timedelta | None
    view_count: int | None
    like_count: int | None
    comment_count: int | None
    last_refreshed_at: datetime
    tags: tuple[str, ...] = ()
    thumbnail_url: str | None = None
    video_url: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "youtube_video_id",
            _require_non_empty("youtube_video_id", self.youtube_video_id),
        )
        object.__setattr__(self, "title", _require_non_empty("title", self.title))
        object.__setattr__(self, "channel_id", _require_non_empty("channel_id", self.channel_id))
        object.__setattr__(
            self,
            "channel_title",
            _require_non_empty("channel_title", self.channel_title),
        )
        object.__setattr__(
            self,
            "published_at",
            _require_optional_utc("published_at", self.published_at),
        )
        object.__setattr__(
            self,
            "last_refreshed_at",
            _require_utc("last_refreshed_at", self.last_refreshed_at),
        )
        object.__setattr__(self, "view_count", _require_non_negative("view_count", self.view_count))
        object.__setattr__(self, "like_count", _require_non_negative("like_count", self.like_count))
        object.__setattr__(
            self,
            "comment_count",
            _require_non_negative("comment_count", self.comment_count),
        )
        object.__setattr__(self, "tags", tuple(tag for tag in self.tags if tag))
        if self.duration is not None and self.duration < timedelta(0):
            msg = "duration must be non-negative when provided"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class Video:
    """A discovered public YouTube video tracked by the research project."""

    youtube_video_id: str
    first_seen_at: datetime
    metadata: YouTubeMetadata

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "youtube_video_id",
            _require_non_empty("youtube_video_id", self.youtube_video_id),
        )
        object.__setattr__(self, "first_seen_at", _require_utc("first_seen_at", self.first_seen_at))
        if self.metadata.youtube_video_id != self.youtube_video_id:
            msg = "metadata youtube_video_id must match video youtube_video_id"
            raise ValueError(msg)

    def with_refreshed_metadata(self, metadata: YouTubeMetadata) -> Video:
        """Return a copy with new metadata while preserving discovery provenance."""

        return Video(
            youtube_video_id=self.youtube_video_id,
            first_seen_at=self.first_seen_at,
            metadata=metadata,
        )


@dataclass(frozen=True, slots=True)
class SearchQuery:
    """A researcher-supplied YouTube search and its project-owned parameters."""

    query_text: str
    parameters: Mapping[str, SearchParameterValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "query_text", _require_non_empty("query_text", self.query_text))
        object.__setattr__(self, "parameters", MappingProxyType(dict(self.parameters)))


@dataclass(frozen=True, slots=True)
class CollectionRun:
    """A single metadata collection attempt for a search query."""

    search_query: SearchQuery
    started_at: datetime
    completed_at: datetime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "started_at", _require_utc("started_at", self.started_at))
        object.__setattr__(
            self,
            "completed_at",
            _require_optional_utc("completed_at", self.completed_at),
        )
        if self.completed_at is not None and self.completed_at < self.started_at:
            msg = "completed_at must not be earlier than started_at"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class SearchHit:
    """The fact that one search returned one video."""

    query: SearchQuery
    youtube_video_id: str
    discovered_at: datetime
    rank: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "youtube_video_id",
            _require_non_empty("youtube_video_id", self.youtube_video_id),
        )
        object.__setattr__(self, "discovered_at", _require_utc("discovered_at", self.discovered_at))
        if self.rank is not None and self.rank < 1:
            msg = "rank must be positive when provided"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class ResearchAnnotation:
    """Researcher-owned notes kept separate from YouTube metadata."""

    youtube_video_id: str
    updated_at: datetime
    review_status: ReviewStatus = ReviewStatus.UNREVIEWED
    notes: str | None = None
    relevance_label: str | None = None
    competition_name: str | None = None
    fencer_names: tuple[str, ...] = ()
    weapon_category: str | None = None
    event_notes: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "youtube_video_id",
            _require_non_empty("youtube_video_id", self.youtube_video_id),
        )
        object.__setattr__(self, "updated_at", _require_utc("updated_at", self.updated_at))
        object.__setattr__(self, "fencer_names", tuple(name for name in self.fencer_names if name))
