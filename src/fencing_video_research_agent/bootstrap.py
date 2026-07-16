"""Composition root for wiring application use cases to infrastructure."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy.engine import Engine

from fencing_video_research_agent.application import (
    ClearAnnotationLabelUseCase,
    CollectVideosUseCase,
    ExportSearchHitsUseCase,
    ExportVideosUseCase,
    SetAnnotationLabelUseCase,
    SetAnnotationNotesUseCase,
    SetAnnotationReviewStatusUseCase,
    ShowAnnotationUseCase,
    UpdateAnnotationUseCase,
)
from fencing_video_research_agent.application.inspect_storage import (
    GetStoredDataSummaryUseCase,
    ListCollectionRunsUseCase,
    ListSearchHitTableRowsUseCase,
    ListStoredVideosUseCase,
    ListVideoTableRowsUseCase,
    ShowCollectionRunUseCase,
    ShowStoredVideoUseCase,
)
from fencing_video_research_agent.infrastructure.clock import SystemClock
from fencing_video_research_agent.infrastructure.exports import (
    PandasSearchHitExportWriter,
    PandasVideoExportWriter,
)
from fencing_video_research_agent.infrastructure.persistence.database import (
    create_database_engine,
    create_session_factory,
)
from fencing_video_research_agent.infrastructure.persistence.export_repositories import (
    SqlAlchemySearchHitExportReader,
    SqlAlchemyVideoExportReader,
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
    """Runtime resources for read-only stored-data inspection."""

    list_videos: ListStoredVideosUseCase
    show_video: ShowStoredVideoUseCase
    list_collection_runs: ListCollectionRunsUseCase
    show_collection_run: ShowCollectionRunUseCase
    engine: Engine

    def close(self) -> None:
        """Dispose of database resources held by the runtime."""

        self.engine.dispose()


@dataclass(frozen=True, slots=True)
class ApiRuntime:
    """Runtime resources for local API workflows."""

    summary: GetStoredDataSummaryUseCase
    list_video_table_rows: ListVideoTableRowsUseCase
    show_video: ShowStoredVideoUseCase
    update_annotation: UpdateAnnotationUseCase
    list_collection_runs: ListCollectionRunsUseCase
    show_collection_run: ShowCollectionRunUseCase
    list_search_hit_table_rows: ListSearchHitTableRowsUseCase
    engine: Engine

    def close(self) -> None:
        """Dispose of database resources held by the runtime."""

        self.engine.dispose()


@dataclass(frozen=True, slots=True)
class AnnotationRuntime:
    """Runtime resources for manual researcher annotation workflows."""

    show_annotation: ShowAnnotationUseCase
    set_review_status: SetAnnotationReviewStatusUseCase
    set_notes: SetAnnotationNotesUseCase
    set_label: SetAnnotationLabelUseCase
    clear_label: ClearAnnotationLabelUseCase
    engine: Engine

    def close(self) -> None:
        """Dispose of database resources held by the runtime."""

        self.engine.dispose()


@dataclass(frozen=True, slots=True)
class ExportVideosRuntime:
    """Runtime resources for video export workflows."""

    use_case: ExportVideosUseCase
    engine: Engine

    def close(self) -> None:
        """Dispose of database resources held by the runtime."""

        self.engine.dispose()


@dataclass(frozen=True, slots=True)
class ExportSearchHitsRuntime:
    """Runtime resources for search-hit provenance export workflows."""

    use_case: ExportSearchHitsUseCase
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


def build_annotation_runtime(settings: AppSettings) -> AnnotationRuntime:
    """Wire manual annotation use cases without constructing YouTube clients."""

    clock = SystemClock()
    engine = create_database_engine(settings.database_url)
    session_factory = create_session_factory(engine)

    def unit_of_work_factory() -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory)

    return AnnotationRuntime(
        show_annotation=ShowAnnotationUseCase(unit_of_work_factory=unit_of_work_factory),
        set_review_status=SetAnnotationReviewStatusUseCase(
            unit_of_work_factory=unit_of_work_factory,
            clock=clock,
        ),
        set_notes=SetAnnotationNotesUseCase(
            unit_of_work_factory=unit_of_work_factory,
            clock=clock,
        ),
        set_label=SetAnnotationLabelUseCase(
            unit_of_work_factory=unit_of_work_factory,
            clock=clock,
        ),
        clear_label=ClearAnnotationLabelUseCase(
            unit_of_work_factory=unit_of_work_factory,
            clock=clock,
        ),
        engine=engine,
    )


def build_export_videos_runtime(settings: AppSettings) -> ExportVideosRuntime:
    """Wire video export use case without constructing YouTube clients."""

    engine = create_database_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    reader = SqlAlchemyVideoExportReader(session_factory)
    writer = PandasVideoExportWriter()
    return ExportVideosRuntime(
        use_case=ExportVideosUseCase(reader=reader, writer=writer),
        engine=engine,
    )


def build_export_search_hits_runtime(settings: AppSettings) -> ExportSearchHitsRuntime:
    """Wire search-hit export use case without constructing YouTube clients."""

    engine = create_database_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    reader = SqlAlchemySearchHitExportReader(session_factory)
    writer = PandasSearchHitExportWriter()
    return ExportSearchHitsRuntime(
        use_case=ExportSearchHitsUseCase(reader=reader, writer=writer),
        engine=engine,
    )


def build_video_inspection_runtime(settings: AppSettings) -> VideoInspectionRuntime:
    """Wire read-only stored-video use cases to persistence infrastructure."""

    engine = create_database_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    stored_data_reader = SqlAlchemyStoredDataReader(session_factory)
    return VideoInspectionRuntime(
        list_videos=ListStoredVideosUseCase(stored_data_reader=stored_data_reader),
        show_video=ShowStoredVideoUseCase(stored_data_reader=stored_data_reader),
        list_collection_runs=ListCollectionRunsUseCase(stored_data_reader=stored_data_reader),
        show_collection_run=ShowCollectionRunUseCase(stored_data_reader=stored_data_reader),
        engine=engine,
    )


def build_api_runtime(settings: AppSettings) -> ApiRuntime:
    """Wire local API use cases without constructing YouTube clients."""

    clock = SystemClock()
    engine = create_database_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    stored_data_reader = SqlAlchemyStoredDataReader(session_factory)

    def unit_of_work_factory() -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory)

    return ApiRuntime(
        summary=GetStoredDataSummaryUseCase(stored_data_reader=stored_data_reader),
        list_video_table_rows=ListVideoTableRowsUseCase(stored_data_reader=stored_data_reader),
        show_video=ShowStoredVideoUseCase(stored_data_reader=stored_data_reader),
        update_annotation=UpdateAnnotationUseCase(
            unit_of_work_factory=unit_of_work_factory,
            clock=clock,
        ),
        list_collection_runs=ListCollectionRunsUseCase(stored_data_reader=stored_data_reader),
        show_collection_run=ShowCollectionRunUseCase(stored_data_reader=stored_data_reader),
        list_search_hit_table_rows=ListSearchHitTableRowsUseCase(
            stored_data_reader=stored_data_reader
        ),
        engine=engine,
    )
