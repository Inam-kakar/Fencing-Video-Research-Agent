"""Tests for read-only stored-video inspection use cases."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import pytest

from fencing_video_research_agent.application import (
    ListStoredVideosRequest,
    ListStoredVideosUseCase,
    ShowStoredVideoRequest,
    ShowStoredVideoUseCase,
    StoredVideoNotFoundError,
)
from fencing_video_research_agent.ports import (
    StoredVideoDetail,
    StoredVideoSummary,
)

NOW = datetime(2026, 7, 13, 8, 0, tzinfo=UTC)


def make_summary(youtube_video_id: str = "video-123") -> StoredVideoSummary:
    """Create a stored-video summary for use-case tests."""

    return StoredVideoSummary(
        youtube_video_id=youtube_video_id,
        title="Sabre final",
        channel_title="Fencing Channel",
        published_at=NOW,
        first_seen_at=NOW,
        last_refreshed_at=NOW,
    )


def make_detail(youtube_video_id: str = "video-123") -> StoredVideoDetail:
    """Create stored-video detail for use-case tests."""

    return StoredVideoDetail(
        youtube_video_id=youtube_video_id,
        title="Sabre final",
        description="A public fencing bout.",
        channel_id="channel-123",
        channel_title="Fencing Channel",
        published_at=NOW,
        duration_seconds=600,
        view_count=100,
        like_count=10,
        comment_count=2,
        tags=("sabre", "final"),
        thumbnail_url="https://example.test/thumb.jpg",
        video_url="https://www.youtube.com/watch?v=video-123",
        first_seen_at=NOW,
        last_refreshed_at=NOW,
        annotation_status="reviewed",
    )


@dataclass
class FakeStoredDataReader:
    """Read-only fake for application tests."""

    summaries: tuple[StoredVideoSummary, ...] = ()
    details_by_id: dict[str, StoredVideoDetail] | None = None
    list_limits: list[int] | None = None
    requested_ids: list[str] | None = None

    def list_videos(self, *, limit: int) -> tuple[StoredVideoSummary, ...]:
        if self.list_limits is not None:
            self.list_limits.append(limit)
        return self.summaries

    def get_video(self, youtube_video_id: str) -> StoredVideoDetail | None:
        if self.requested_ids is not None:
            self.requested_ids.append(youtube_video_id)
        return (self.details_by_id or {}).get(youtube_video_id)


def test_list_stored_videos_returns_reader_summaries() -> None:
    limits: list[int] = []
    reader = FakeStoredDataReader(summaries=(make_summary(),), list_limits=limits)
    use_case = ListStoredVideosUseCase(stored_data_reader=reader)

    result = use_case.execute(ListStoredVideosRequest(limit=5))

    assert limits == [5]
    assert [video.youtube_video_id for video in result.videos] == ["video-123"]


def test_list_stored_videos_accepts_empty_result() -> None:
    reader = FakeStoredDataReader()
    use_case = ListStoredVideosUseCase(stored_data_reader=reader)

    result = use_case.execute(ListStoredVideosRequest(limit=20))

    assert result.videos == ()


def test_list_stored_videos_rejects_invalid_limits() -> None:
    with pytest.raises(ValueError, match="positive"):
        ListStoredVideosRequest(limit=0)
    with pytest.raises(ValueError, match="at most"):
        ListStoredVideosRequest(limit=101)


def test_show_stored_video_returns_reader_detail() -> None:
    requested_ids: list[str] = []
    reader = FakeStoredDataReader(
        details_by_id={"video-123": make_detail()},
        requested_ids=requested_ids,
    )
    use_case = ShowStoredVideoUseCase(stored_data_reader=reader)

    result = use_case.execute(ShowStoredVideoRequest(youtube_video_id=" video-123 "))

    assert requested_ids == ["video-123"]
    assert result.video.title == "Sabre final"


def test_show_stored_video_raises_for_missing_video() -> None:
    reader = FakeStoredDataReader(details_by_id={})
    use_case = ShowStoredVideoUseCase(stored_data_reader=reader)

    with pytest.raises(StoredVideoNotFoundError) as error:
        use_case.execute(ShowStoredVideoRequest(youtube_video_id="missing-video"))

    assert error.value.youtube_video_id == "missing-video"
