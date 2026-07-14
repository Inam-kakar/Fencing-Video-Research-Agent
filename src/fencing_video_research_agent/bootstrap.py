"""Composition root for wiring application use cases to infrastructure."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy.engine import Engine

from fencing_video_research_agent.application import (
    CollectVideosUseCase,
    ListStoredVideosUseCase,
    ShowStoredVideoUseCase,
)
from fencing_video_research_agent.infrastructure.clock import SystemClock
from fencing_video_research_agent.infrastructure.persistence.database import (
    create_database_engine,
    create_session_factory,
)
from fencing_video_research_agent.infrastructure.persistence.read_repositories import (
    SqlAlchemyStoredDataReader,
)
from fencing_video_research_agent.infrastructure.persistence.unit_of_work import (
    SqlAlchemyUnitOfWork,
)
from fencing_video_research_agent.infrastructure.settings import AppSettings, ConfigurationError
from fencing_video_research_agent.infrastructure.youtube import (
    YouTubeDataApiGateway,
    create_youtube_data_api_client,
)
from fencing_video_research_agent.ports import UnitOfWork

type UnitOfWorkFactory = Callable[[], UnitOfWork]


@dataclass(frozen=True, slots=True)
class CollectVideosRuntime:
    """Runtime resources for one composed collection workflow."""

    use_case: CollectVideosUseCase
    engine: Engine

    def close(self) -> None:
        """Dispose of database resources held by the runtime."""

        self.engine.dispose()


@dataclass(frozen=True, slots=True)
class VideoInspectionRuntime:
    """Runtime resources for read-only stored-video inspection."""

    list_videos: ListStoredVideosUseCase
    show_video: ShowStoredVideoUseCase
    engine: Engine

    def close(self) -> None:
        """Dispose of database resources held by the runtime."""

        self.engine.dispose()


def build_collect_videos_runtime(settings: AppSettings) -> CollectVideosRuntime:
    """Wire the collect-videos use case to concrete infrastructure."""

    if not settings.youtube_api_key.get_secret_value().strip():
        msg = "Missing or invalid configuration: YOUTUBE_API_KEY is required"
        raise ConfigurationError(msg)

    clock = SystemClock()
    youtube_client = create_youtube_data_api_client(settings.youtube_api_key)
    youtube_gateway = YouTubeDataApiGateway(client=youtube_client, clock=clock)
    engine = create_database_engine(settings.database_url)
    session_factory = create_session_factory(engine)

    def unit_of_work_factory() -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory)

    use_case = CollectVideosUseCase(
        youtube_gateway=youtube_gateway,
        unit_of_work_factory=unit_of_work_factory,
        clock=clock,
    )
    return CollectVideosRuntime(use_case=use_case, engine=engine)


def build_video_inspection_runtime(settings: AppSettings) -> VideoInspectionRuntime:
    """Wire read-only stored-video use cases to persistence infrastructure."""

    engine = create_database_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    stored_data_reader = SqlAlchemyStoredDataReader(session_factory)
    return VideoInspectionRuntime(
        list_videos=ListStoredVideosUseCase(stored_data_reader=stored_data_reader),
        show_video=ShowStoredVideoUseCase(stored_data_reader=stored_data_reader),
        engine=engine,
    )
