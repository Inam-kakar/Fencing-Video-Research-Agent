"""Tests for local-development CORS on the API."""

from fastapi.testclient import TestClient


def test_local_vite_origin_is_allowed_for_gets(api_client: TestClient) -> None:
    response = api_client.get("/health", headers={"Origin": "http://localhost:5173"})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_local_vite_origin_is_allowed_for_patch_preflight(
    api_client: TestClient,
) -> None:
    response = api_client.options(
        "/api/videos/video-123/annotation",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "PATCH",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "PATCH" in response.headers["access-control-allow-methods"]
    assert "content-type" in response.headers["access-control-allow-headers"].lower()


def test_local_vite_origin_is_allowed_for_post_preflight(
    api_client: TestClient,
) -> None:
    response = api_client.options(
        "/api/collection-runs",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "POST" in response.headers["access-control-allow-methods"]
    assert "content-type" in response.headers["access-control-allow-headers"].lower()


def test_unlisted_origin_is_not_allowed(api_client: TestClient) -> None:
    response = api_client.get("/health", headers={"Origin": "http://localhost:5174"})

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers
