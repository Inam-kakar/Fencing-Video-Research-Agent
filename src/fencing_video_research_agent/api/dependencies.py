"""FastAPI dependency helpers for API routes."""

from __future__ import annotations

from typing import cast

from fastapi import Request

from fencing_video_research_agent.bootstrap import ApiRuntime


def get_api_runtime(request: Request) -> ApiRuntime:
    """Return the API runtime attached by the app factory."""

    return cast(ApiRuntime, request.app.state.api_runtime)
