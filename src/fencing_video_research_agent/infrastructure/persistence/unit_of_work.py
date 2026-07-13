"""SQLAlchemy Unit of Work implementation."""

from __future__ import annotations

from types import TracebackType
from typing import Self

from sqlalchemy.orm import Session, sessionmaker

from fencing_video_research_agent.infrastructure.persistence.repositories import (
    SqlAlchemyAnnotationRepository,
    SqlAlchemyCollectionRepository,
    SqlAlchemyVideoRepository,
)


class SqlAlchemyUnitOfWork:
    """Transaction boundary backed by one SQLAlchemy session."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self._session: Session | None = None
        self._committed = False
        self._videos: SqlAlchemyVideoRepository | None = None
        self._collections: SqlAlchemyCollectionRepository | None = None
        self._annotations: SqlAlchemyAnnotationRepository | None = None

    @property
    def videos(self) -> SqlAlchemyVideoRepository:
        """Video repository bound to the active transaction."""

        if self._videos is None:
            msg = "unit of work is not active"
            raise RuntimeError(msg)
        return self._videos

    @property
    def collections(self) -> SqlAlchemyCollectionRepository:
        """Collection repository bound to the active transaction."""

        if self._collections is None:
            msg = "unit of work is not active"
            raise RuntimeError(msg)
        return self._collections

    @property
    def annotations(self) -> SqlAlchemyAnnotationRepository:
        """Annotation repository bound to the active transaction."""

        if self._annotations is None:
            msg = "unit of work is not active"
            raise RuntimeError(msg)
        return self._annotations

    def __enter__(self) -> Self:
        """Open a session and bind repositories to it."""

        self._session = self._session_factory()
        self._committed = False
        self._videos = SqlAlchemyVideoRepository(self._session)
        self._collections = SqlAlchemyCollectionRepository(self._session)
        self._annotations = SqlAlchemyAnnotationRepository(self._session)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Rollback uncommitted work and close the active session."""

        del exc, traceback
        if self._session is None:
            return
        try:
            if exc_type is not None or not self._committed:
                self._session.rollback()
        finally:
            self._session.close()
            self._session = None
            self._videos = None
            self._collections = None
            self._annotations = None
            self._committed = False

    def commit(self) -> None:
        """Commit pending changes in the active transaction."""

        session = self._require_session()
        session.commit()
        self._committed = True

    def rollback(self) -> None:
        """Rollback pending changes in the active transaction."""

        session = self._require_session()
        session.rollback()
        self._committed = False

    def _require_session(self) -> Session:
        if self._session is None:
            msg = "unit of work is not active"
            raise RuntimeError(msg)
        return self._session
