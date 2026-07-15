"""Tests for read-only API summary endpoint."""

from fastapi.testclient import TestClient
from tests.api.conftest import (
    ApiDatabase,
    seed_annotation,
    seed_collection_run,
    seed_video,
)

from fencing_video_research_agent.domain import ReviewStatus


def test_summary_returns_zero_counts_for_empty_database(api_client: TestClient) -> None:
    response = api_client.get("/api/summary")

    assert response.status_code == 200
    assert response.json() == {
        "video_count": 0,
        "collection_run_count": 0,
        "search_hit_count": 0,
        "annotation_count": 0,
        "reviewed_count": 0,
        "unreviewed_count": 0,
    }


def test_summary_counts_stored_data_and_unannotated_videos(
    api_client: TestClient,
    api_database: ApiDatabase,
) -> None:
    seed_video(api_database.session_factory, "reviewed-video", title="Reviewed")
    seed_video(api_database.session_factory, "unreviewed-video", title="Unreviewed")
    seed_annotation(
        api_database.session_factory,
        "reviewed-video",
        review_status=ReviewStatus.REVIEWED,
    )
    seed_collection_run(api_database.session_factory, youtube_video_id="reviewed-video")

    response = api_client.get("/api/summary")

    assert response.status_code == 200
    assert response.json() == {
        "video_count": 2,
        "collection_run_count": 1,
        "search_hit_count": 1,
        "annotation_count": 1,
        "reviewed_count": 1,
        "unreviewed_count": 1,
    }
