"""FastAPI app factory for local research data endpoints."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fencing_video_research_agent.api.routes import health, runs, search_hits, summary, videos
from fencing_video_research_agent.bootstrap import build_api_runtime
from fencing_video_research_agent.infrastructure.migrations import ensure_database_current
from fencing_video_research_agent.infrastructure.settings import AppSettings, load_settings

LOCAL_FRONTEND_ORIGIN = "http://localhost:5173"


def create_app(
    *,
    settings: AppSettings | None = None,
    database_url: str | None = None,
    run_migrations: bool = True,
) -> FastAPI:
    """Create the FastAPI app with injectable settings for tests."""

    resolved_settings = settings or load_settings(require_youtube_api_key=False)
    if database_url is not None:
        resolved_settings = resolved_settings.model_copy(update={"database_url": database_url})

    if run_migrations:
        ensure_database_current(resolved_settings.database_url)

    runtime = build_api_runtime(resolved_settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        del app
        try:
            yield
        finally:
            runtime.close()

    app = FastAPI(
        title="Fencing Video Research Agent API",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[LOCAL_FRONTEND_ORIGIN],
        allow_methods=["GET", "PATCH"],
        allow_headers=["content-type"],
        allow_credentials=False,
    )
    app.state.api_runtime = runtime
    app.include_router(health.router)
    app.include_router(summary.router)
    app.include_router(videos.router)
    app.include_router(runs.router)
    app.include_router(search_hits.router)
    return app
