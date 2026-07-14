"""Application use cases for read-only stored-video inspection."""

from __future__ import annotations

from dataclasses import dataclass

from fencing_video_research_agent.ports import (
    StoredDataReader,
    StoredVideoDetail,
    StoredVideoSummary,
)

MAX_STORED_VIDEO_LIST_LIMIT = 100


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


class StoredVideoNotFoundError(Exception):
    """Raised when a requested stored video does not exist."""

    def __init__(self, youtube_video_id: str) -> None:
        self.youtube_video_id = youtube_video_id
        super().__init__(f"stored video not found: {youtube_video_id}")


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
