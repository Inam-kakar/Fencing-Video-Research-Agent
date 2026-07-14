"""Application use cases for read-only stored-video inspection."""

from __future__ import annotations

from dataclasses import dataclass

from fencing_video_research_agent.ports import (
    CollectionRunRecordId,
    StoredCollectionRunDetail,
    StoredCollectionRunSummary,
    StoredDataReader,
    StoredVideoDetail,
    StoredVideoSummary,
)

MAX_STORED_VIDEO_LIST_LIMIT = 100
MAX_COLLECTION_RUN_LIST_LIMIT = 100


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

    def __post_init__(self) -> None:
        if self.limit < 1:
            msg = "limit must be positive"
            raise ValueError(msg)
        if self.limit > MAX_COLLECTION_RUN_LIST_LIMIT:
            msg = f"limit must be at most {MAX_COLLECTION_RUN_LIST_LIMIT}"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class ListCollectionRunsResult:
    """Read-only result for collection-run listing."""

    runs: tuple[StoredCollectionRunSummary, ...]


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
            runs=self._stored_data_reader.list_collection_runs(limit=request.limit),
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
