"""Application use cases for read-only stored-video inspection."""

from __future__ import annotations

from dataclasses import dataclass

from fencing_video_research_agent.ports import CollectionRunRecordId
from fencing_video_research_agent.ports.stored_data import (
    StoredCollectionRunDetail,
    StoredCollectionRunSummary,
    StoredDataReader,
    StoredDataSummary,
    StoredSearchHitTableRow,
    StoredVideoDetail,
    StoredVideoSummary,
    StoredVideoTableRow,
)

MAX_STORED_VIDEO_LIST_LIMIT = 100
MAX_COLLECTION_RUN_LIST_LIMIT = 100
MAX_API_TABLE_LIMIT = 100


@dataclass(frozen=True, slots=True)
class GetStoredDataSummaryRequest:
    """Input for reading dashboard-oriented stored-data counts."""


@dataclass(frozen=True, slots=True)
class GetStoredDataSummaryResult:
    """Dashboard-oriented stored-data count result."""

    summary: StoredDataSummary


@dataclass(frozen=True, slots=True)
class ListStoredVideosRequest:
    """Input for listing stored videos."""

    limit: int = 20

    def __post_init__(self) -> None:
        if self.limit < 1:
            msg = "limit must be positive"
            raise ValueError(msg)
        if self.limit > MAX_STORED_VIDEO_LIST_LIMIT:
            msg = f"limit must be at most {MAX_STORED_VIDEO_LIST_LIMIT}"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class ListStoredVideosResult:
    """Read-only result for stored-video listing."""

    videos: tuple[StoredVideoSummary, ...]


@dataclass(frozen=True, slots=True)
class ListVideoTableRowsRequest:
    """Input for listing API-friendly stored-video table rows."""

    limit: int = 20
    offset: int = 0
    search: str | None = None

    def __post_init__(self) -> None:
        _validate_limit(self.limit)
        if self.offset < 0:
            msg = "offset must not be negative"
            raise ValueError(msg)
        object.__setattr__(self, "search", _optional_text(self.search))


@dataclass(frozen=True, slots=True)
class ListVideoTableRowsResult:
    """Read-only result for API-friendly stored-video table rows."""

    videos: tuple[StoredVideoTableRow, ...]


@dataclass(frozen=True, slots=True)
class ShowStoredVideoRequest:
    """Input for inspecting one stored video."""

    youtube_video_id: str

    def __post_init__(self) -> None:
        youtube_video_id = self.youtube_video_id.strip()
        if not youtube_video_id:
            msg = "youtube_video_id must not be empty"
            raise ValueError(msg)
        object.__setattr__(self, "youtube_video_id", youtube_video_id)


@dataclass(frozen=True, slots=True)
class ShowStoredVideoResult:
    """Read-only result for one stored video."""

    video: StoredVideoDetail


@dataclass(frozen=True, slots=True)
class ListCollectionRunsRequest:
    """Input for listing stored collection runs."""

    limit: int = 20
    offset: int = 0

    def __post_init__(self) -> None:
        if self.limit < 1:
            msg = "limit must be positive"
            raise ValueError(msg)
        if self.limit > MAX_COLLECTION_RUN_LIST_LIMIT:
            msg = f"limit must be at most {MAX_COLLECTION_RUN_LIST_LIMIT}"
            raise ValueError(msg)
        if self.offset < 0:
            msg = "offset must not be negative"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class ListCollectionRunsResult:
    """Read-only result for collection-run listing."""

    runs: tuple[StoredCollectionRunSummary, ...]


@dataclass(frozen=True, slots=True)
class ListSearchHitTableRowsRequest:
    """Input for listing API-friendly search-hit provenance table rows."""

    limit: int = 20
    offset: int = 0
    query_text: str | None = None

    def __post_init__(self) -> None:
        _validate_limit(self.limit)
        if self.offset < 0:
            msg = "offset must not be negative"
            raise ValueError(msg)
        object.__setattr__(self, "query_text", _optional_text(self.query_text))


@dataclass(frozen=True, slots=True)
class ListSearchHitTableRowsResult:
    """Read-only result for API-friendly search-hit provenance rows."""

    search_hits: tuple[StoredSearchHitTableRow, ...]


@dataclass(frozen=True, slots=True)
class ShowCollectionRunRequest:
    """Input for inspecting one stored collection run."""

    run_id: int

    def __post_init__(self) -> None:
        if self.run_id < 1:
            msg = "run_id must be positive"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class ShowCollectionRunResult:
    """Read-only result for one stored collection run."""

    run: StoredCollectionRunDetail


class StoredVideoNotFoundError(Exception):
    """Raised when a requested stored video does not exist."""

    def __init__(self, youtube_video_id: str) -> None:
        self.youtube_video_id = youtube_video_id
        super().__init__(f"stored video not found: {youtube_video_id}")


class StoredCollectionRunNotFoundError(Exception):
    """Raised when a requested stored collection run does not exist."""

    def __init__(self, run_id: int) -> None:
        self.run_id = run_id
        super().__init__(f"stored collection run not found: {run_id}")


class ListStoredVideosUseCase:
    """List videos already stored in the local research database."""

    def __init__(self, *, stored_data_reader: StoredDataReader) -> None:
        self._stored_data_reader = stored_data_reader

    def execute(self, request: ListStoredVideosRequest) -> ListStoredVideosResult:
        """Return stored video summaries without collecting new data."""

        return ListStoredVideosResult(
            videos=self._stored_data_reader.list_videos(limit=request.limit),
        )


class GetStoredDataSummaryUseCase:
    """Read dashboard-oriented counts from the local research database."""

    def __init__(self, *, stored_data_reader: StoredDataReader) -> None:
        self._stored_data_reader = stored_data_reader

    def execute(self, request: GetStoredDataSummaryRequest) -> GetStoredDataSummaryResult:
        """Return stored-data counts without collecting new data."""

        del request
        return GetStoredDataSummaryResult(summary=self._stored_data_reader.get_summary())


class ListVideoTableRowsUseCase:
    """List API-friendly stored-video rows for a future dashboard."""

    def __init__(self, *, stored_data_reader: StoredDataReader) -> None:
        self._stored_data_reader = stored_data_reader

    def execute(self, request: ListVideoTableRowsRequest) -> ListVideoTableRowsResult:
        """Return stored-video table rows without collecting new data."""

        return ListVideoTableRowsResult(
            videos=self._stored_data_reader.list_video_table_rows(
                limit=request.limit,
                offset=request.offset,
                search=request.search,
            ),
        )


class ShowStoredVideoUseCase:
    """Inspect one video already stored in the local research database."""

    def __init__(self, *, stored_data_reader: StoredDataReader) -> None:
        self._stored_data_reader = stored_data_reader

    def execute(self, request: ShowStoredVideoRequest) -> ShowStoredVideoResult:
        """Return stored video details without collecting new data."""

        video = self._stored_data_reader.get_video(request.youtube_video_id)
        if video is None:
            raise StoredVideoNotFoundError(request.youtube_video_id)
        return ShowStoredVideoResult(video=video)


class ListCollectionRunsUseCase:
    """List collection runs already stored in the local research database."""

    def __init__(self, *, stored_data_reader: StoredDataReader) -> None:
        self._stored_data_reader = stored_data_reader

    def execute(self, request: ListCollectionRunsRequest) -> ListCollectionRunsResult:
        """Return stored collection-run summaries without collecting new data."""

        return ListCollectionRunsResult(
            runs=self._stored_data_reader.list_collection_runs(
                limit=request.limit,
                offset=request.offset,
            ),
        )


class ShowCollectionRunUseCase:
    """Inspect one collection run already stored in the local research database."""

    def __init__(self, *, stored_data_reader: StoredDataReader) -> None:
        self._stored_data_reader = stored_data_reader

    def execute(self, request: ShowCollectionRunRequest) -> ShowCollectionRunResult:
        """Return collection-run details without collecting new data."""

        run = self._stored_data_reader.get_collection_run(
            CollectionRunRecordId(request.run_id),
        )
        if run is None:
            raise StoredCollectionRunNotFoundError(request.run_id)
        return ShowCollectionRunResult(run=run)


class ListSearchHitTableRowsUseCase:
    """List API-friendly search-hit provenance rows for a future dashboard."""

    def __init__(self, *, stored_data_reader: StoredDataReader) -> None:
        self._stored_data_reader = stored_data_reader

    def execute(self, request: ListSearchHitTableRowsRequest) -> ListSearchHitTableRowsResult:
        """Return search-hit provenance rows without collecting new data."""

        return ListSearchHitTableRowsResult(
            search_hits=self._stored_data_reader.list_search_hit_table_rows(
                limit=request.limit,
                offset=request.offset,
                query_text=request.query_text,
            ),
        )


def _validate_limit(limit: int) -> None:
    if limit < 1:
        msg = "limit must be positive"
        raise ValueError(msg)
    if limit > MAX_API_TABLE_LIMIT:
        msg = f"limit must be at most {MAX_API_TABLE_LIMIT}"
        raise ValueError(msg)


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    return stripped
