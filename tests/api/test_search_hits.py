"""Tests for read-only API search-hit provenance endpoints."""

from fastapi.testclient import TestClient
from tests.api.conftest import (
    ApiDatabase,
    seed_annotation,
    seed_collection_run,
    seed_video,
)


def test_search_hits_returns_empty_list_for_empty_database(api_client: TestClient) -> None:
    response = api_client.get("/api/search-hits")

    assert response.status_code == 200
    assert response.json() == {"items": [], "count": 0, "limit": 20, "offset": 0}


def test_search_hits_returns_provenance_rows(
    api_client: TestClient,
    api_database: ApiDatabase,
) -> None:
    seed_video(api_database.session_factory, "video-123", title="Sabre final")
    seed_annotation(api_database.session_factory, "video-123", relevance_label="relevant")
    run_id = seed_collection_run(
        api_database.session_factory,
        youtube_video_id="video-123",
        rank=3,
    )

    response = api_client.get("/api/search-hits")

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["items"][0]["collection_run_id"] == run_id
    assert body["items"][0]["query_text"] == "sabre fencing final"
    assert body["items"][0]["rank"] == 3
    assert body["items"][0]["youtube_video_id"] == "video-123"
    assert body["items"][0]["title"] == "Sabre final"
    assert body["items"][0]["channel_title"] == "Fencing Channel"
    assert body["items"][0]["review_status"] == "reviewed"
    assert body["items"][0]["relevance_label"] == "relevant"
    assert body["items"][0]["run_started_at"] is not None
    assert body["items"][0]["discovered_at"] is not None


def test_search_hits_supports_query_text_filter(
    api_client: TestClient,
    api_database: ApiDatabase,
) -> None:
    seed_video(api_database.session_factory, "sabre-video", title="Sabre final")
    seed_video(api_database.session_factory, "foil-video", title="Foil final")
    seed_collection_run(
        api_database.session_factory,
        query_text="sabre fencing final",
        youtube_video_id="sabre-video",
    )
    seed_collection_run(
        api_database.session_factory,
        query_text="foil fencing final",
        youtube_video_id="foil-video",
    )

    response = api_client.get("/api/search-hits", params={"query_text": "sabre"})

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["items"][0]["youtube_video_id"] == "sabre-video"
    assert body["items"][0]["query_text"] == "sabre fencing final"
