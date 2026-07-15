"""Tests for local-development CORS on the read-only API."""

from fastapi.testclient import TestClient


def test_local_vite_origin_is_allowed_for_read_only_gets(api_client: TestClient) -> None:
    response = api_client.get("/health", headers={"Origin": "http://localhost:5173"})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_unlisted_origin_is_not_allowed(api_client: TestClient) -> None:
    response = api_client.get("/health", headers={"Origin": "http://localhost:5174"})

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers
