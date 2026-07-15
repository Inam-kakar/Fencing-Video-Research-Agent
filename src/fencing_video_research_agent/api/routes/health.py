"""Health-check route for the read-only API."""

from __future__ import annotations

from fastapi import APIRouter

from fencing_video_research_agent.api.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Return a simple API health response."""

    return HealthResponse(status="ok")
