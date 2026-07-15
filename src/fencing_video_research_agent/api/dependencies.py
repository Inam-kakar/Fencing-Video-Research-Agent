"""FastAPI dependency helpers for read-only API routes."""

from __future__ import annotations

from typing import cast

from fastapi import Request

from fencing_video_research_agent.bootstrap import ApiReadRuntime


def get_api_read_runtime(request: Request) -> ApiReadRuntime:
    """Return the read-only API runtime attached by the app factory."""

    return cast(ApiReadRuntime, request.app.state.api_read_runtime)
