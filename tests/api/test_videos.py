"""Tests for read-only API video endpoints."""

from fastapi.testclient import TestClient
from tests.api.conftest import (
    ApiDatabase,
    seed_annotation,
    seed_collection_run,
    seed_video,
)


def test_videos_returns_empty_list_for_empty_database(api_client: TestClient) -> None:
    response = api_client.get("/api/videos")

    assert response.status_code == 200
    assert response.json() == {"items": [], "count": 0, "limit": 20, "offset": 0}


def test_videos_returns_stored_video_rows(
    api_client: TestClient,
    api_database: ApiDatabase,
) -> None:
    seed_video(api_database.session_factory, "video-123", title="Sabre final")
    seed_annotation(api_database.session_factory, "video-123", relevance_label="relevant")

    response = api_client.get("/api/videos")

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["items"][0]["youtube_video_id"] == "video-123"
    assert body["items"][0]["title"] == "Sabre final"
    assert body["items"][0]["channel_title"] == "Fencing Channel"
    assert body["items"][0]["duration_seconds"] == 720
    assert body["items"][0]["view_count"] == 100
    assert body["items"][0]["review_status"] == "reviewed"
    assert body["items"][0]["relevance_label"] == "relevant"
    assert body["items"][0]["video_url"] == "https://www.youtube.com/watch?v=video-123"


def test_videos_supports_simple_search(
    api_client: TestClient,
    api_database: ApiDatabase,
) -> None:
    seed_video(api_database.session_factory, "video-one", title="Sabre final")
    seed_video(api_database.session_factory, "video-two", title="Foil lesson")

    response = api_client.get("/api/videos", params={"search": "sabre"})

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["items"][0]["youtube_video_id"] == "video-one"


def test_video_detail_returns_metadata_annotation_and_provenance(
    api_client: TestClient,
    api_database: ApiDatabase,
) -> None:
    seed_video(api_database.session_factory, "video-123", title="Sabre final")
    seed_annotation(api_database.session_factory, "video-123", relevance_label="relevant")
    seed_collection_run(api_database.session_factory, youtube_video_id="video-123")

    response = api_client.get("/api/videos/video-123")

    assert response.status_code == 200
    body = response.json()
    assert body["youtube_video_id"] == "video-123"
    assert body["title"] == "Sabre final"
    assert body["description"] == "A public sabre fencing bout."
    assert body["channel_id"] == "channel-123"
    assert body["tags"] == ["sabre", "final"]
    assert body["review_status"] == "reviewed"
    assert body["notes"] == "Useful reference."
    assert body["relevance_label"] == "relevant"
    assert body["competition_name"] == "European Championship"
    assert body["fencer_names"] == ["Fencer One", "Fencer Two"]
    assert body["weapon_category"] == "sabre"
    assert body["event_notes"] == "Final bout"
    assert body["discovery_run_count"] == 1
    assert body["first_query_text"] == "sabre fencing final"
    assert body["latest_query_text"] == "sabre fencing final"


def test_missing_video_returns_safe_404(api_client: TestClient) -> None:
    response = api_client.get("/api/videos/missing-video")

    assert response.status_code == 404
    assert response.json() == {"detail": "Stored video not found"}
