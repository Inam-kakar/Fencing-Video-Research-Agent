"""Collection-run mutation routes for the API."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from fencing_video_research_agent.api.dependencies import get_api_runtime
from fencing_video_research_agent.api.schemas import (
    CollectionRunCreateResponse,
)
from fencing_video_research_agent.api.schemas import (
    CreateCollectionRunRequest as CreateCollectionRunBody,
)
from fencing_video_research_agent.application import (
    CollectVideosRequest,
    MissingYouTubeMetadataError,
)
from fencing_video_research_agent.bootstrap import ApiRuntime
from fencing_video_research_agent.ports import YouTubeGatewayError

router = APIRouter(prefix="/api/collection-runs", tags=["collection-runs"])


@router.post("", response_model=CollectionRunCreateResponse)
def create_collection_run(
    payload: CreateCollectionRunBody,
    runtime: Annotated[ApiRuntime, Depends(get_api_runtime)],
) -> CollectionRunCreateResponse:
    """Run controlled YouTube metadata collection through the backend."""

    if runtime.collect_videos is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="YouTube API key is required for collection",
        )

    try:
        result = runtime.collect_videos.execute(
            CollectVideosRequest(
                query_text=payload.query,
                max_results=payload.max_results,
            )
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except (MissingYouTubeMetadataError, YouTubeGatewayError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="YouTube metadata collection failed",
        ) from exc

    return CollectionRunCreateResponse.from_result(result)
