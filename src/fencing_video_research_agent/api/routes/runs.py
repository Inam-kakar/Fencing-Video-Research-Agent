"""Collection-run routes for the read-only API."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from fencing_video_research_agent.api.dependencies import get_api_read_runtime
from fencing_video_research_agent.api.schemas import (
    RunDetailResponse,
    RunListItemResponse,
    RunListResponse,
)
from fencing_video_research_agent.application.inspect_storage import (
    ListCollectionRunsRequest,
    ShowCollectionRunRequest,
    StoredCollectionRunNotFoundError,
)
from fencing_video_research_agent.bootstrap import ApiReadRuntime

router = APIRouter(prefix="/api/runs", tags=["runs"])


@router.get("", response_model=RunListResponse)
def list_runs(
    runtime: Annotated[ApiReadRuntime, Depends(get_api_read_runtime)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> RunListResponse:
    """Return collection-run rows for frontend table views."""

    request = ListCollectionRunsRequest(limit=limit, offset=offset)
    result = runtime.list_collection_runs.execute(request)
    items = [RunListItemResponse.from_row(run) for run in result.runs]
    return RunListResponse(items=items, count=len(items), limit=limit, offset=offset)


@router.get("/{run_id}", response_model=RunDetailResponse)
def show_run(
    run_id: Annotated[int, Path(ge=1)],
    runtime: Annotated[ApiReadRuntime, Depends(get_api_read_runtime)],
) -> RunDetailResponse:
    """Return one collection-run detail with returned videos."""

    try:
        result = runtime.show_collection_run.execute(ShowCollectionRunRequest(run_id=run_id))
    except StoredCollectionRunNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection run not found",
        ) from exc
    return RunDetailResponse.from_detail(result.run)
