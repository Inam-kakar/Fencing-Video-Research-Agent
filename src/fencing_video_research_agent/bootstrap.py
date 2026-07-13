"""Composition root for wiring application use cases to infrastructure."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy.engine import Engine

from fencing_video_research_agent.application import CollectVideosUseCase
from fencing_video_research_agent.infrastructure.clock import SystemClock
from fencing_video_research_agent.infrastructure.persistence.database import (
    create_database_engine,
    create_session_factory,
)
from fencing_video_research_agent.infrastructure.persistence.unit_of_work import (
    SqlAlchemyUnitOfWork,
)
from fencing_video_research_agent.infrastructure.settings import AppSettings
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


def build_collect_videos_runtime(settings: AppSettings) -> CollectVideosRuntime:
    """Wire the collect-videos use case to concrete infrastructure."""

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
