"""Stored-video routes for the read-only API."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from fencing_video_research_agent.api.dependencies import get_api_read_runtime
from fencing_video_research_agent.api.schemas import (
    VideoDetailResponse,
    VideoListItemResponse,
    VideoListResponse,
)
from fencing_video_research_agent.application.inspect_storage import (
    ListVideoTableRowsRequest,
    ShowStoredVideoRequest,
    StoredVideoNotFoundError,
)
from fencing_video_research_agent.bootstrap import ApiReadRuntime

router = APIRouter(prefix="/api/videos", tags=["videos"])


@router.get("", response_model=VideoListResponse)
def list_videos(
    runtime: Annotated[ApiReadRuntime, Depends(get_api_read_runtime)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    search: Annotated[str | None, Query()] = None,
) -> VideoListResponse:
    """Return stored video rows for frontend table views."""

    request = ListVideoTableRowsRequest(limit=limit, offset=offset, search=search)
    result = runtime.list_video_table_rows.execute(request)
    items = [VideoListItemResponse.from_row(video) for video in result.videos]
    return VideoListResponse(items=items, count=len(items), limit=limit, offset=offset)


@router.get("/{youtube_video_id}", response_model=VideoDetailResponse)
def show_video(
    youtube_video_id: str,
    runtime: Annotated[ApiReadRuntime, Depends(get_api_read_runtime)],
) -> VideoDetailResponse:
    """Return one stored video detail."""

    try:
        result = runtime.show_video.execute(
            ShowStoredVideoRequest(youtube_video_id=youtube_video_id)
        )
    except StoredVideoNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stored video not found",
        ) from exc
    return VideoDetailResponse.from_detail(result.video)
