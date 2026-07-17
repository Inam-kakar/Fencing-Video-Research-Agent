"""Tests for browser-triggered collection-run API endpoint."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from tests.api.conftest import ApiDatabase

from fencing_video_research_agent import bootstrap
from fencing_video_research_agent.api.main import create_app
from fencing_video_research_agent.domain import YouTubeMetadata
from fencing_video_research_agent.infrastructure.settings import AppSettings
from fencing_video_research_agent.ports import (
    TransientYouTubeGatewayError,
    YouTubeSearchRequest,
    YouTubeSearchResult,
)

NOW = datetime(2026, 7, 16, 10, 0, tzinfo=UTC)


@dataclass
class FakeGatewayState:
    """Configurable fake YouTube gateway state for API tests."""

    search_results: tuple[YouTubeSearchResult, ...]
    metadata: tuple[YouTubeMetadata, ...]
    search_error: Exception | None = None
    search_requests: list[YouTubeSearchRequest] | None = None
    metadata_requests: list[tuple[str, ...]] | None = None

    def __post_init__(self) -> None:
        self.search_requests = []
        self.metadata_requests = []


def make_metadata(youtube_video_id: str, *, title: str | None = None) -> YouTubeMetadata:
    """Create project-owned metadata for fake YouTube collection tests."""

    return YouTubeMetadata(
        youtube_video_id=youtube_video_id,
        title=title or f"Sabre bout {youtube_video_id}",
        description="A public sabre fencing bout.",
        channel_id="channel-123",
        channel_title="Fencing Channel",
        published_at=NOW - timedelta(days=1),
        duration=timedelta(minutes=10),
        view_count=100,
        like_count=10,
        comment_count=2,
        tags=("sabre",),
        thumbnail_url="https://example.test/thumb.jpg",
        video_url=f"https://www.youtube.com/watch?v={youtube_video_id}",
        last_refreshed_at=NOW,
    )


def make_client_with_fake_gateway(
    *,
    api_database: ApiDatabase,
    monkeypatch: pytest.MonkeyPatch,
    search_results: Sequence[YouTubeSearchResult],
    metadata: Sequence[YouTubeMetadata],
    search_error: Exception | None = None,
) -> tuple[TestClient, FakeGatewayState]:
    """Create a TestClient wired to a fake YouTube gateway."""

    state = FakeGatewayState(
        search_results=tuple(search_results),
        metadata=tuple(metadata),
        search_error=search_error,
    )

    def fake_create_youtube_data_api_client(api_key: SecretStr) -> object:
        assert api_key.get_secret_value() == "test-youtube-api-key"
        return object()

    class FakeYouTubeGateway:
        """Fake gateway class matching the infrastructure adapter constructor."""

        def __init__(self, *, client: object, clock: object) -> None:
            del client, clock

        def search_videos(
            self,
            request: YouTubeSearchRequest,
        ) -> tuple[YouTubeSearchResult, ...]:
            assert state.search_requests is not None
            state.search_requests.append(request)
            if state.search_error is not None:
                raise state.search_error
            return state.search_results

        def fetch_video_metadata(
            self,
            video_ids: Sequence[str],
        ) -> tuple[YouTubeMetadata, ...]:
            assert state.metadata_requests is not None
            state.metadata_requests.append(tuple(video_ids))
            return state.metadata

    monkeypatch.setattr(
        bootstrap,
        "create_youtube_data_api_client",
        fake_create_youtube_data_api_client,
    )
    monkeypatch.setattr(bootstrap, "YouTubeDataApiGateway", FakeYouTubeGateway)
    settings = AppSettings.model_construct(
        youtube_api_key=SecretStr("test-youtube-api-key"),
        database_url=api_database.database_url,
        log_level="INFO",
    )
    return TestClient(create_app(settings=settings)), state


def test_post_collection_run_succeeds_with_fake_youtube_gateway(
    api_database: ApiDatabase,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, gateway_state = make_client_with_fake_gateway(
        api_database=api_database,
        monkeypatch=monkeypatch,
        search_results=(
            YouTubeSearchResult(youtube_video_id="video-1", rank=1),
            YouTubeSearchResult(youtube_video_id="video-2", rank=2),
        ),
        metadata=(make_metadata("video-1"), make_metadata("video-2")),
    )

    with client:
        response = client.post(
            "/api/collection-runs",
            json={"query": " Sandro Bazadze fencing sabre ", "max_results": 2},
        )
        runs_response = client.get("/api/runs")
        hits_response = client.get("/api/search-hits")

    assert response.status_code == 200
    assert response.json() == {
        "collection_run_id": 1,
        "query": "Sandro Bazadze fencing sabre",
        "max_results": 2,
        "videos_found": 2,
        "videos_stored": 2,
        "search_hits_recorded": 2,
        "status": "completed",
    }
    assert gateway_state.search_requests is not None
    assert gateway_state.search_requests[0].query_text == "Sandro Bazadze fencing sabre"
    assert gateway_state.search_requests[0].max_results == 2
    assert gateway_state.metadata_requests == [("video-1", "video-2")]
    assert runs_response.status_code == 200
    assert runs_response.json()["items"][0]["query_text"] == "Sandro Bazadze fencing sabre"
    assert hits_response.status_code == 200
    assert hits_response.json()["count"] == 2


def test_post_collection_run_uses_safe_default_max_results(
    api_database: ApiDatabase,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, gateway_state = make_client_with_fake_gateway(
        api_database=api_database,
        monkeypatch=monkeypatch,
        search_results=(),
        metadata=(),
    )

    with client:
        response = client.post(
            "/api/collection-runs",
            json={"query": "Sandro Bazadze fencing sabre"},
        )

    assert response.status_code == 200
    assert response.json()["max_results"] == 10
    assert gateway_state.search_requests is not None
    assert gateway_state.search_requests[0].max_results == 10


def test_post_collection_run_reuses_duplicate_video_results(
    api_database: ApiDatabase,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _gateway_state = make_client_with_fake_gateway(
        api_database=api_database,
        monkeypatch=monkeypatch,
        search_results=(
            YouTubeSearchResult(youtube_video_id="video-1", rank=1),
            YouTubeSearchResult(youtube_video_id="video-1", rank=2),
        ),
        metadata=(make_metadata("video-1"),),
    )

    with client:
        response = client.post(
            "/api/collection-runs",
            json={"query": "duplicate sabre video", "max_results": 2},
        )
        hits_response = client.get("/api/search-hits")

    assert response.status_code == 200
    assert response.json()["videos_found"] == 2
    assert response.json()["videos_stored"] == 1
    assert response.json()["search_hits_recorded"] == 1
    assert hits_response.json()["count"] == 1


def test_post_collection_run_requires_backend_youtube_api_key(
    api_client: TestClient,
) -> None:
    response = api_client.post(
        "/api/collection-runs",
        json={"query": "Sandro Bazadze fencing sabre", "max_results": 5},
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "YouTube API key is required for collection"}


def test_post_collection_run_returns_safe_error_for_youtube_gateway_failure(
    api_database: ApiDatabase,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _gateway_state = make_client_with_fake_gateway(
        api_database=api_database,
        monkeypatch=monkeypatch,
        search_results=(),
        metadata=(),
        search_error=TransientYouTubeGatewayError("test-youtube-api-key must not leak"),
    )

    with client:
        response = client.post(
            "/api/collection-runs",
            json={"query": "Sandro Bazadze fencing sabre", "max_results": 5},
        )

    assert response.status_code == 502
    assert response.json() == {"detail": "YouTube metadata collection failed"}
    assert "test-youtube-api-key" not in response.text


def test_post_collection_run_validates_request_body(api_client: TestClient) -> None:
    cases = [
        ({"max_results": 5}, 422),
        ({"query": "   ", "max_results": 5}, 422),
        ({"query": "sabre", "max_results": 0}, 422),
        ({"query": "sabre", "max_results": 26}, 422),
        ({"query": "sabre", "max_results": 5, "order": "date"}, 422),
    ]

    for payload, expected_status in cases:
        response = api_client.post("/api/collection-runs", json=payload)
        assert response.status_code == expected_status
