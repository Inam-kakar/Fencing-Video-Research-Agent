"""Stored-video routes for the API."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from fencing_video_research_agent.api.dependencies import get_api_runtime
from fencing_video_research_agent.api.schemas import (
    UpdateVideoAnnotationRequest as UpdateVideoAnnotationBody,
)
from fencing_video_research_agent.api.schemas import (
    VideoAnnotationResponse,
    VideoDetailResponse,
    VideoListItemResponse,
    VideoListResponse,
)
from fencing_video_research_agent.application import (
    AnnotationVideoNotFoundError,
    InvalidReviewStatusError,
    UpdateAnnotationRequest,
)
from fencing_video_research_agent.application.inspect_storage import (
    ListVideoTableRowsRequest,
    ShowStoredVideoRequest,
    StoredVideoNotFoundError,
)
from fencing_video_research_agent.bootstrap import ApiRuntime

router = APIRouter(prefix="/api/videos", tags=["videos"])


@router.get("", response_model=VideoListResponse)
def list_videos(
    runtime: Annotated[ApiRuntime, Depends(get_api_runtime)],
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
    runtime: Annotated[ApiRuntime, Depends(get_api_runtime)],
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


@router.patch("/{youtube_video_id}/annotation", response_model=VideoAnnotationResponse)
def update_video_annotation(
    youtube_video_id: str,
    payload: UpdateVideoAnnotationBody,
    runtime: Annotated[ApiRuntime, Depends(get_api_runtime)],
) -> VideoAnnotationResponse:
    """Update browser-editable annotation fields for one stored video."""

    provided_fields = payload.model_fields_set
    try:
        result = runtime.update_annotation.execute(
            UpdateAnnotationRequest(
                youtube_video_id=youtube_video_id,
                review_status=payload.review_status,
                relevance_label=payload.relevance_label,
                notes=payload.notes,
                update_review_status="review_status" in provided_fields,
                update_relevance_label="relevance_label" in provided_fields,
                update_notes="notes" in provided_fields,
            )
        )
    except AnnotationVideoNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stored video not found",
        ) from exc
    except (InvalidReviewStatusError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return VideoAnnotationResponse.from_annotation(result.annotation)
