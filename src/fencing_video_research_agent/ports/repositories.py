"""Repository port contracts for Phase 1 persistence."""

from __future__ import annotations

from datetime import datetime
from typing import NewType, Protocol

from fencing_video_research_agent.domain import (
    CollectionRun,
    ResearchAnnotation,
    SearchQuery,
    Video,
)

VideoRecordId = NewType("VideoRecordId", int)
SearchQueryRecordId = NewType("SearchQueryRecordId", int)
CollectionRunRecordId = NewType("CollectionRunRecordId", int)


class RepositoryError(Exception):
    """Base class for repository failures."""


class VideoNotFoundError(RepositoryError):
    """Raised when a repository operation requires a stored video."""


class CollectionRunNotFoundError(RepositoryError):
    """Raised when a repository operation requires a stored collection run."""


class IncompleteVideoRecordError(RepositoryError):
    """Raised when stored video rows cannot be mapped to a complete domain video."""


class VideoRepository(Protocol):
    """Persistence boundary for stored videos and latest YouTube metadata."""

    def get_by_youtube_id(self, youtube_video_id: str) -> Video | None:
        """Return a domain video by YouTube ID, if it exists."""

    def add_or_update(self, video: Video) -> VideoRecordId:
        """Insert a video or update its latest metadata."""


class CollectionRepository(Protocol):
    """Persistence boundary for search queries, collection runs, and search hits."""

    def get_or_create_search_query(
        self,
        query: SearchQuery,
        *,
        created_at: datetime,
    ) -> SearchQueryRecordId:
        """Return the existing search query handle or create one."""

    def add_collection_run(
        self,
        run: CollectionRun,
        *,
        status: str,
        error_message: str | None = None,
    ) -> CollectionRunRecordId:
        """Record one collection run for the run's search query."""

    def add_search_hit(
        self,
        collection_run_id: CollectionRunRecordId,
        *,
        youtube_video_id: str,
        discovered_at: datetime,
        rank: int | None = None,
    ) -> None:
        """Record that one collection run returned one stored video."""


class AnnotationRepository(Protocol):
    """Persistence boundary for researcher-owned annotations."""

    def get_by_youtube_id(self, youtube_video_id: str) -> ResearchAnnotation | None:
        """Return the annotation for a YouTube video, if it exists."""

    def save(self, annotation: ResearchAnnotation) -> None:
        """Insert or update a researcher annotation."""
