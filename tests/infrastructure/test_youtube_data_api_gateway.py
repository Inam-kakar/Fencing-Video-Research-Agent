
"""Tests for the official YouTube Data API gateway adapter."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import pytest
from googleapiclient.errors import HttpError
from pydantic import SecretStr

from fencing_video_research_agent.infrastructure.clock import SystemClock
from fencing_video_research_agent.infrastructure.settings import ConfigurationError
from fencing_video_research_agent.infrastructure.youtube import (
    VIDEO_PARTS,
    YouTubeDataApiGateway,
    create_youtube_data_api_client,
)
from fencing_video_research_agent.ports import (
    PermanentYouTubeGatewayError,
    TransientYouTubeGatewayError,
    YouTubeSearchRequest,
)

NOW = datetime(2026, 7, 13, 12, 0, tzinfo=UTC)


type FakeResponse = Mapping[str, object]
type FakeOutcome = FakeResponse | Exception


class FakeClock:
    """Deterministic clock for metadata refresh timestamps."""

    def utcnow(self) -> datetime:
        return NOW


class FakeExecutable:
    """Fake executable Google API request."""

    def __init__(self, outcomes: list[FakeOutcome]) -> None:
        self._outcomes = outcomes

    def execute(self) -> Mapping[str, object]:
        if not self._outcomes:
            raise AssertionError("unexpected Google API execute call")
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


@dataclass
class FakeResource:
    """Fake Google API resource that records list calls."""

    outcomes: list[FakeOutcome]
    calls: list[dict[str, object]] = field(default_factory=list)

    def list(self, **kwargs: object) -> FakeExecutable:
        self.calls.append(dict(kwargs))
        return FakeExecutable(self.outcomes)


@dataclass
class FakeYouTubeClient:
    """Fake YouTube Data API client with search and videos resources."""

    search_resource: FakeResource = field(default_factory=lambda: FakeResource([]))
    videos_resource: FakeResource = field(default_factory=lambda: FakeResource([]))

    def search(self) -> FakeResource:
        return self.search_resource

    def videos(self) -> FakeResource:
        return self.videos_resource


class FakeHttpResponse(dict[str, str]):
    """Minimal response object accepted by googleapiclient HttpError."""

    def __init__(self, *, status: int, reason: str) -> None:
        super().__init__()
        self.status = status
        self.reason = reason

    def getheaders(self) -> dict[str, str]:
        return {}


def http_error(status: int, reason: str) -> HttpError:
    """Create a Google HttpError without making a network request."""

    content = json.dumps(
        {
            "error": {
                "code": status,
                "errors": [
                    {
                        "reason": reason,
                        "message": "sanitized fake error",
                    }
                ],
            }
        }
    ).encode("utf-8")
    return HttpError(FakeHttpResponse(status=status, reason=reason), content)


def search_item(video_id: str, *, published_at: str = "2026-07-12T10:30:00Z") -> dict[str, object]:
    """Return one fabricated search.list item."""

    return {
        "id": {"videoId": video_id},
        "snippet": {
            "title": f"Sabre bout {video_id}",
            "channelId": "channel-123",
            "channelTitle": "Fencing Channel",
            "publishedAt": published_at,
        },
    }


def video_item(
    video_id: str,
    *,
    duration: str = "PT9M30S",
    published_at: str = "2026-07-12T10:30:00Z",
) -> dict[str, object]:
    """Return one fabricated videos.list item."""

    return {
        "id": video_id,
        "snippet": {
            "title": "Sabre semifinal",
            "description": "A sabre fencing bout.",
            "channelId": "channel-123",
            "channelTitle": "Fencing Channel",
            "publishedAt": published_at,
            "tags": ["sabre", "fencing"],
            "thumbnails": {
                "high": {
                    "url": "https://example.test/high.jpg",
                }
            },
        },
        "contentDetails": {
            "duration": duration,
        },
        "statistics": {
            "viewCount": "120",
            "likeCount": "15",
            "commentCount": "3",
        },
    }


def make_gateway(
    *,
    search_outcomes: Sequence[FakeOutcome] = (),
    video_outcomes: Sequence[FakeOutcome] = (),
    max_retries: int = 2,
    sleep_calls: list[float] | None = None,
) -> tuple[YouTubeDataApiGateway, FakeYouTubeClient, list[float]]:
    """Build the gateway with a fake Google client."""

    sleep_delays = sleep_calls if sleep_calls is not None else []
    client = FakeYouTubeClient(
        search_resource=FakeResource(list(search_outcomes)),
        videos_resource=FakeResource(list(video_outcomes)),
    )
    gateway = YouTubeDataApiGateway(
        client=client,
        clock=FakeClock(),
        max_retries=max_retries,
        retry_sleep_seconds=0.25,
        sleep=sleep_delays.append,
    )
    return gateway, client, sleep_delays


def test_create_youtube_client_uses_official_google_discovery_build(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []
    fake_client = FakeYouTubeClient()

    def fake_build(service_name: str, version: str, **kwargs: object) -> FakeYouTubeClient:
        calls.append({"service_name": service_name, "version": version, **kwargs})
        return fake_client

    monkeypatch.setattr("fencing_video_research_agent.infrastructure.youtube.build", fake_build)

    client = create_youtube_data_api_client(SecretStr("test-api-key"))

    assert client is fake_client
    assert calls == [
        {
            "service_name": "youtube",
            "version": "v3",
            "developerKey": "test-api-key",
            "cache_discovery": False,
        }
    ]


def test_create_youtube_client_rejects_blank_api_key() -> None:
    with pytest.raises(ConfigurationError, match="YOUTUBE_API_KEY"):
        create_youtube_data_api_client("")


def test_system_clock_returns_timezone_aware_utc_datetime() -> None:
    now = SystemClock().utcnow()

    assert now.tzinfo is UTC


def test_search_list_uses_snippet_part_and_video_type() -> None:
    gateway, client, _ = make_gateway(
        search_outcomes=({"items": [search_item("video-1")]},),
    )

    results = gateway.search_videos(
        YouTubeSearchRequest(query_text="sabre fencing", max_results=1),
    )

    assert [result.youtube_video_id for result in results] == ["video-1"]
    assert client.search_resource.calls[0]["part"] == "snippet"
    assert client.search_resource.calls[0]["type"] == "video"
    assert client.search_resource.calls[0]["q"] == "sabre fencing"
    assert client.search_resource.calls[0]["maxResults"] == 1


def test_supported_search_parameters_are_passed_through() -> None:
    gateway, client, _ = make_gateway(search_outcomes=({"items": []},))

    gateway.search_videos(
        YouTubeSearchRequest(
            query_text="sabre fencing",
            max_results=1,
            parameters={
                "order": "date",
                "regionCode": "US",
                "videoEmbeddable": True,
            },
        )
    )

    assert client.search_resource.calls[0]["order"] == "date"
    assert client.search_resource.calls[0]["regionCode"] == "US"
    assert client.search_resource.calls[0]["videoEmbeddable"] is True


def test_unsupported_search_parameters_raise_permanent_error() -> None:
    gateway, client, _ = make_gateway(search_outcomes=({"items": []},))

    with pytest.raises(PermanentYouTubeGatewayError, match="Unsupported"):
        gateway.search_videos(
            YouTubeSearchRequest(
                query_text="sabre fencing",
                max_results=1,
                parameters={"forbiddenParameter": "value"},
            )
        )

    assert client.search_resource.calls == []


def test_adapter_controlled_search_parameters_cannot_be_overridden() -> None:
    gateway, client, _ = make_gateway(search_outcomes=({"items": []},))

    with pytest.raises(PermanentYouTubeGatewayError, match="override"):
        gateway.search_videos(
            YouTubeSearchRequest(
                query_text="sabre fencing",
                max_results=1,
                parameters={"maxResults": 50},
            )
        )

    assert client.search_resource.calls == []


def test_search_pagination_follows_next_page_token_until_max_results() -> None:
    gateway, client, _ = make_gateway(
        search_outcomes=(
            {
                "items": [search_item("video-1"), search_item("video-2")],
                "nextPageToken": "next-page",
            },
            {"items": [search_item("video-3")]},
        ),
    )

    results = gateway.search_videos(
        YouTubeSearchRequest(query_text="sabre fencing", max_results=3),
    )

    assert [(result.youtube_video_id, result.rank) for result in results] == [
        ("video-1", 1),
        ("video-2", 2),
        ("video-3", 3),
    ]
    assert client.search_resource.calls[0]["maxResults"] == 3
    assert client.search_resource.calls[1]["maxResults"] == 1
    assert client.search_resource.calls[1]["pageToken"] == "next-page"


def test_empty_search_results_return_empty_tuple() -> None:
    gateway, _client, _ = make_gateway(search_outcomes=({"items": []},))

    results = gateway.search_videos(
        YouTubeSearchRequest(query_text="sabre fencing", max_results=10),
    )

    assert results == ()


def test_search_results_map_video_ids_and_snippets_to_project_types() -> None:
    gateway, _client, _ = make_gateway(
        search_outcomes=({"items": [search_item("video-1")]},),
    )

    result = gateway.search_videos(
        YouTubeSearchRequest(query_text="sabre fencing", max_results=1),
    )[0]

    assert result.youtube_video_id == "video-1"
    assert result.rank == 1
    assert result.title == "Sabre bout video-1"
    assert result.channel_id == "channel-123"
    assert result.channel_title == "Fencing Channel"
    assert result.published_at == datetime(2026, 7, 12, 10, 30, tzinfo=UTC)


def test_missing_search_result_video_id_raises_permanent_error() -> None:
    gateway, _client, _ = make_gateway(search_outcomes=({"items": [{"id": {}}]},))

    with pytest.raises(PermanentYouTubeGatewayError, match="videoId"):
        gateway.search_videos(
            YouTubeSearchRequest(query_text="sabre fencing", max_results=1),
        )


def test_videos_list_deduplicates_and_batches_ids() -> None:
    first_batch_ids = [f"video-{index}" for index in range(1, 51)]
    second_batch_ids = ["video-51"]
    gateway, client, _ = make_gateway(
        video_outcomes=(
            {"items": [video_item(video_id) for video_id in first_batch_ids]},
            {"items": [video_item("video-51")]},
        )
    )

    metadata = gateway.fetch_video_metadata([*first_batch_ids, "video-1", *second_batch_ids])

    assert len(metadata) == 51
    assert client.videos_resource.calls[0]["id"] == ",".join(first_batch_ids)
    assert client.videos_resource.calls[1]["id"] == "video-51"


def test_videos_list_requests_required_parts() -> None:
    gateway, client, _ = make_gateway(
        video_outcomes=({"items": [video_item("video-1")]},),
    )

    gateway.fetch_video_metadata(["video-1"])

    assert client.videos_resource.calls[0]["part"] == VIDEO_PARTS


def test_metadata_maps_video_fields_to_project_owned_metadata() -> None:
    gateway, _client, _ = make_gateway(
        video_outcomes=({"items": [video_item("video-1")]},),
    )

    metadata = gateway.fetch_video_metadata(["video-1"])[0]

    assert metadata.youtube_video_id == "video-1"
    assert metadata.title == "Sabre semifinal"
    assert metadata.description == "A sabre fencing bout."
    assert metadata.channel_id == "channel-123"
    assert metadata.channel_title == "Fencing Channel"
    assert metadata.published_at == datetime(2026, 7, 12, 10, 30, tzinfo=UTC)
    assert metadata.duration == timedelta(minutes=9, seconds=30)
    assert metadata.view_count == 120
    assert metadata.like_count == 15
    assert metadata.comment_count == 3
    assert metadata.tags == ("sabre", "fencing")
    assert metadata.thumbnail_url == "https://example.test/high.jpg"
    assert metadata.video_url == "https://www.youtube.com/watch?v=video-1"
    assert metadata.last_refreshed_at == NOW


def test_missing_optional_metadata_fields_become_none_or_empty_tuple() -> None:
    gateway, _client, _ = make_gateway(
        video_outcomes=(
            {
                "items": [
                    {
                        "id": "video-1",
                        "snippet": {
                            "title": "Sabre semifinal",
                            "channelId": "channel-123",
                            "channelTitle": "Fencing Channel",
                        },
                    }
                ]
            },
        ),
    )

    metadata = gateway.fetch_video_metadata(["video-1"])[0]

    assert metadata.description is None
    assert metadata.published_at is None
    assert metadata.duration is None
    assert metadata.view_count is None
    assert metadata.like_count is None
    assert metadata.comment_count is None
    assert metadata.tags == ()
    assert metadata.thumbnail_url is None


def test_invalid_iso_duration_raises_permanent_error() -> None:
    gateway, _client, _ = make_gateway(
        video_outcomes=({"items": [video_item("video-1", duration="invalid")]},),
    )

    with pytest.raises(PermanentYouTubeGatewayError, match="duration"):
        gateway.fetch_video_metadata(["video-1"])


def test_invalid_publication_timestamp_raises_permanent_error() -> None:
    gateway, _client, _ = make_gateway(
        video_outcomes=({"items": [video_item("video-1", published_at="not-a-date")]},),
    )

    with pytest.raises(PermanentYouTubeGatewayError, match="datetime"):
        gateway.fetch_video_metadata(["video-1"])


def test_missing_required_metadata_field_raises_permanent_error() -> None:
    item = video_item("video-1")
    item["snippet"] = {
        "description": "missing required title",
        "channelId": "channel-123",
        "channelTitle": "Fencing Channel",
    }
    gateway, _client, _ = make_gateway(video_outcomes=({"items": [item]},))

    with pytest.raises(PermanentYouTubeGatewayError, match="title"):
        gateway.fetch_video_metadata(["video-1"])


def test_transient_http_errors_retry_and_then_succeed() -> None:
    gateway, client, sleep_calls = make_gateway(
        search_outcomes=(
            http_error(503, "backendError"),
            {"items": [search_item("video-1")]},
        ),
        max_retries=1,
    )

    results = gateway.search_videos(
        YouTubeSearchRequest(query_text="sabre fencing", max_results=1),
    )

    assert [result.youtube_video_id for result in results] == ["video-1"]
    assert len(client.search_resource.calls) == 1
    assert sleep_calls == [0.25]


def test_exhausted_transient_retries_raise_transient_error() -> None:
    gateway, _client, sleep_calls = make_gateway(
        search_outcomes=(
            http_error(503, "backendError"),
            http_error(503, "backendError"),
        ),
        max_retries=1,
    )

    with pytest.raises(TransientYouTubeGatewayError, match="after retries"):
        gateway.search_videos(
            YouTubeSearchRequest(query_text="sabre fencing", max_results=1),
        )

    assert sleep_calls == [0.25]


def test_quota_errors_raise_sanitized_permanent_error_without_retry() -> None:
    gateway, client, sleep_calls = make_gateway(
        search_outcomes=(http_error(403, "quotaExceeded"),),
        max_retries=2,
    )

    with pytest.raises(PermanentYouTubeGatewayError) as error:
        gateway.search_videos(
            YouTubeSearchRequest(query_text="sabre fencing", max_results=1),
        )

    assert "quota" in str(error.value).lower()
    assert "test-api-key" not in str(error.value)
    assert len(client.search_resource.calls) == 1
    assert sleep_calls == []


def test_permanent_api_errors_are_not_retried() -> None:
    gateway, client, sleep_calls = make_gateway(
        search_outcomes=(http_error(400, "invalidParameter"),),
        max_retries=2,
    )

    with pytest.raises(PermanentYouTubeGatewayError, match="Permanent"):
        gateway.search_videos(
            YouTubeSearchRequest(query_text="sabre fencing", max_results=1),
        )

    assert len(client.search_resource.calls) == 1
    assert sleep_calls == []


def test_no_live_api_call_or_real_api_key_is_required() -> None:
    gateway, client, _ = make_gateway(search_outcomes=({"items": []},))

    results = gateway.search_videos(YouTubeSearchRequest(query_text="sabre fencing", max_results=1))

    assert results == ()
    assert len(client.search_resource.calls) == 1
