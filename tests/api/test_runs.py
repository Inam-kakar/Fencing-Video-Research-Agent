"""Tests for read-only API collection-run endpoints."""

from fastapi.testclient import TestClient
from tests.api.conftest import ApiDatabase, seed_collection_run, seed_video


def test_runs_returns_empty_list_for_empty_database(api_client: TestClient) -> None:
    response = api_client.get("/api/runs")

    assert response.status_code == 200
    assert response.json() == {"items": [], "count": 0, "limit": 20, "offset": 0}


def test_runs_returns_collection_run_rows(
    api_client: TestClient,
    api_database: ApiDatabase,
) -> None:
    seed_video(api_database.session_factory, "video-123")
    run_id = seed_collection_run(api_database.session_factory, youtube_video_id="video-123")

    response = api_client.get("/api/runs")

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["items"][0]["run_id"] == run_id
    assert body["items"][0]["query_text"] == "sabre fencing final"
    assert body["items"][0]["status"] == "completed"
    assert body["items"][0]["hit_count"] == 1


def test_run_detail_returns_returned_videos(
    api_client: TestClient,
    api_database: ApiDatabase,
) -> None:
    seed_video(api_database.session_factory, "video-123", title="Sabre final")
    run_id = seed_collection_run(
        api_database.session_factory,
        youtube_video_id="video-123",
        rank=2,
    )

    response = api_client.get(f"/api/runs/{run_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["run_id"] == run_id
    assert body["query_text"] == "sabre fencing final"
    assert body["query_parameters"] == {"max_results": 5}
    assert body["status"] == "completed"
    assert body["hit_count"] == 1
    assert body["hits"] == [
        {
            "rank": 2,
            "youtube_video_id": "video-123",
            "title": "Sabre final",
            "channel_title": "Fencing Channel",
        }
    ]


def test_missing_run_returns_safe_404(api_client: TestClient) -> None:
    response = api_client.get("/api/runs/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Collection run not found"}
