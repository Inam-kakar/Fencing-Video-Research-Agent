"""Tests for browser annotation editing through the FastAPI API."""

from fastapi.testclient import TestClient
from tests.api.conftest import (
    ApiDatabase,
    seed_annotation,
    seed_video,
)

from fencing_video_research_agent.domain import ReviewStatus


def test_patch_annotation_updates_review_status(
    api_client: TestClient,
    api_database: ApiDatabase,
) -> None:
    seed_video(api_database.session_factory, "video-123")

    response = api_client.patch(
        "/api/videos/video-123/annotation",
        json={"review_status": "reviewed"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["youtube_video_id"] == "video-123"
    assert body["review_status"] == "reviewed"
    assert body["relevance_label"] is None
    assert body["notes"] is None
    assert body["updated_at"] is not None


def test_patch_annotation_updates_relevance_label(
    api_client: TestClient,
    api_database: ApiDatabase,
) -> None:
    seed_video(api_database.session_factory, "video-123")

    response = api_client.patch(
        "/api/videos/video-123/annotation",
        json={"relevance_label": "olympic-sabre-final"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["review_status"] == "unreviewed"
    assert body["relevance_label"] == "olympic-sabre-final"


def test_patch_annotation_clears_relevance_label_with_null(
    api_client: TestClient,
    api_database: ApiDatabase,
) -> None:
    seed_video(api_database.session_factory, "video-123")
    seed_annotation(api_database.session_factory, "video-123", relevance_label="candidate")

    response = api_client.patch(
        "/api/videos/video-123/annotation",
        json={"relevance_label": None},
    )

    assert response.status_code == 200
    assert response.json()["relevance_label"] is None


def test_patch_annotation_clears_relevance_label_with_empty_string(
    api_client: TestClient,
    api_database: ApiDatabase,
) -> None:
    seed_video(api_database.session_factory, "video-123")
    seed_annotation(api_database.session_factory, "video-123", relevance_label="candidate")

    response = api_client.patch(
        "/api/videos/video-123/annotation",
        json={"relevance_label": "   "},
    )

    assert response.status_code == 200
    assert response.json()["relevance_label"] is None


def test_patch_annotation_updates_notes(
    api_client: TestClient,
    api_database: ApiDatabase,
) -> None:
    seed_video(api_database.session_factory, "video-123")

    response = api_client.patch(
        "/api/videos/video-123/annotation",
        json={"notes": "Useful full sabre final footage."},
    )

    assert response.status_code == 200
    assert response.json()["notes"] == "Useful full sabre final footage."


def test_patch_annotation_clears_notes_with_null_or_blank(
    api_client: TestClient,
    api_database: ApiDatabase,
) -> None:
    seed_video(api_database.session_factory, "video-123")
    seed_annotation(api_database.session_factory, "video-123")

    null_response = api_client.patch(
        "/api/videos/video-123/annotation",
        json={"notes": None},
    )
    blank_response = api_client.patch(
        "/api/videos/video-123/annotation",
        json={"notes": "   "},
    )

    assert null_response.status_code == 200
    assert null_response.json()["notes"] is None
    assert blank_response.status_code == 200
    assert blank_response.json()["notes"] is None


def test_patch_annotation_updates_multiple_fields_and_preserves_richer_fields(
    api_client: TestClient,
    api_database: ApiDatabase,
) -> None:
    seed_video(api_database.session_factory, "video-123")
    seed_annotation(
        api_database.session_factory,
        "video-123",
        review_status=ReviewStatus.UNREVIEWED,
        relevance_label="candidate",
    )

    response = api_client.patch(
        "/api/videos/video-123/annotation",
        json={
            "review_status": "reviewed",
            "relevance_label": "high-value",
            "notes": "Reviewed in browser.",
        },
    )
    detail_response = api_client.get("/api/videos/video-123")

    assert response.status_code == 200
    body = response.json()
    assert body["review_status"] == "reviewed"
    assert body["relevance_label"] == "high-value"
    assert body["notes"] == "Reviewed in browser."
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["competition_name"] == "European Championship"
    assert detail["fencer_names"] == ["Fencer One", "Fencer Two"]
    assert detail["weapon_category"] == "sabre"
    assert detail["event_notes"] == "Final bout"


def test_patch_annotation_returns_safe_404_for_missing_video(
    api_client: TestClient,
) -> None:
    response = api_client.patch(
        "/api/videos/missing-video/annotation",
        json={"review_status": "reviewed"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Stored video not found"}


def test_patch_annotation_rejects_invalid_review_status(
    api_client: TestClient,
    api_database: ApiDatabase,
) -> None:
    seed_video(api_database.session_factory, "video-123")

    response = api_client.patch(
        "/api/videos/video-123/annotation",
        json={"review_status": "relevant"},
    )

    assert response.status_code == 422


def test_patch_annotation_rejects_empty_body(
    api_client: TestClient,
    api_database: ApiDatabase,
) -> None:
    seed_video(api_database.session_factory, "video-123")

    response = api_client.patch("/api/videos/video-123/annotation", json={})

    assert response.status_code == 422


def test_patch_annotation_rejects_unknown_fields(
    api_client: TestClient,
    api_database: ApiDatabase,
) -> None:
    seed_video(api_database.session_factory, "video-123")

    response = api_client.patch(
        "/api/videos/video-123/annotation",
        json={"competition_name": "Do not edit this here"},
    )

    assert response.status_code == 422


def test_patch_annotation_does_not_require_youtube_api_key(
    api_client: TestClient,
    api_database: ApiDatabase,
) -> None:
    seed_video(api_database.session_factory, "video-123")

    response = api_client.patch(
        "/api/videos/video-123/annotation",
        json={"review_status": "reviewed"},
    )

    assert response.status_code == 200
    assert response.json()["review_status"] == "reviewed"
