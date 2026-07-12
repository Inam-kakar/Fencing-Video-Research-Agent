"""Tests for project-owned YouTube port contracts."""

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

import pytest

from fencing_video_research_agent.domain import YouTubeMetadata
from fencing_video_research_agent.ports import (
    YouTubeGateway,
    YouTubeSearchRequest,
    YouTubeSearchResult,
)

NOW = datetime(2026, 2, 3, 4, 5, 6, tzinfo=UTC)


def make_metadata(youtube_video_id: str) -> YouTubeMetadata:
    """Create valid project-owned metadata for fake gateway tests."""

    return YouTubeMetadata(
        youtube_video_id=youtube_video_id,
        title="Sabre semifinal",
        description=None,
        channel_id="channel-123",
        channel_title="Fencing Channel",
        published_at=NOW - timedelta(days=1),
        duration=timedelta(minutes=8),
        view_count=None,
        like_count=None,
        comment_count=None,
        last_refreshed_at=NOW,
        tags=(),
        thumbnail_url=None,
        video_url=None,
    )


class FakeYouTubeGateway:
    """Offline fake that satisfies the YouTube gateway protocol."""

    def search_videos(self, request: YouTubeSearchRequest) -> tuple[YouTubeSearchResult, ...]:
        return tuple(
            YouTubeSearchResult(youtube_video_id=f"video-{index}", rank=index)
            for index in range(1, request.max_results + 1)
        )

    def fetch_video_metadata(self, video_ids: Sequence[str]) -> tuple[YouTubeMetadata, ...]:
        return tuple(make_metadata(video_id) for video_id in video_ids)


def collect_video_ids(gateway: YouTubeGateway) -> tuple[str, ...]:
    """Exercise the protocol without depending on a concrete adapter."""

    results = gateway.search_videos(YouTubeSearchRequest(query_text="sabre fencing", max_results=2))
    return tuple(result.youtube_video_id for result in results)


def test_youtube_gateway_protocol_uses_project_owned_types() -> None:
    gateway = FakeYouTubeGateway()

    video_ids = collect_video_ids(gateway)
    metadata = gateway.fetch_video_metadata(video_ids)

    assert video_ids == ("video-1", "video-2")
    assert [item.youtube_video_id for item in metadata] == ["video-1", "video-2"]


def test_search_request_copies_parameters_and_rejects_invalid_limit() -> None:
    parameters = {"order": "relevance"}

    request = YouTubeSearchRequest(
        query_text="sabre fencing",
        max_results=10,
        parameters=parameters,
    )
    parameters["order"] = "date"

    assert request.parameters["order"] == "relevance"
    with pytest.raises(ValueError, match="max_results"):
        YouTubeSearchRequest(query_text="sabre fencing", max_results=0)


def test_search_result_rejects_naive_publication_timestamp() -> None:
    with pytest.raises(ValueError, match="published_at"):
        YouTubeSearchResult(
            youtube_video_id="video-123",
            rank=1,
            published_at=datetime(2026, 2, 3, 4, 5, 6),
        )
