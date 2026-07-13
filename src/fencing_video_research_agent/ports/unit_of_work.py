"""Unit of Work port for transactional persistence workflows."""

from __future__ import annotations

from types import TracebackType
from typing import Protocol, Self

from fencing_video_research_agent.ports.repositories import (
    AnnotationRepository,
    CollectionRepository,
    VideoRepository,
)


class UnitOfWork(Protocol):
    """Transaction boundary for repository operations."""

    @property
    def videos(self) -> VideoRepository:
        """Video repository bound to the current transaction."""

    @property
    def collections(self) -> CollectionRepository:
        """Collection repository bound to the current transaction."""

    @property
    def annotations(self) -> AnnotationRepository:
        """Annotation repository bound to the current transaction."""

    def __enter__(self) -> Self:
        """Open the transaction resources."""

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Close transaction resources, rolling back when needed."""

    def commit(self) -> None:
        """Persist all pending changes."""

    def rollback(self) -> None:
        """Discard all pending changes."""
