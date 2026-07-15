"""Search-hit provenance routes for the read-only API."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from fencing_video_research_agent.api.dependencies import get_api_read_runtime
from fencing_video_research_agent.api.schemas import (
    SearchHitListItemResponse,
    SearchHitListResponse,
)
from fencing_video_research_agent.application.inspect_storage import (
    ListSearchHitTableRowsRequest,
)
from fencing_video_research_agent.bootstrap import ApiReadRuntime

router = APIRouter(prefix="/api/search-hits", tags=["search-hits"])


@router.get("", response_model=SearchHitListResponse)
def list_search_hits(
    runtime: Annotated[ApiReadRuntime, Depends(get_api_read_runtime)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    query_text: Annotated[str | None, Query()] = None,
) -> SearchHitListResponse:
    """Return search-hit provenance rows for frontend table views."""

    request = ListSearchHitTableRowsRequest(
        limit=limit,
        offset=offset,
        query_text=query_text,
    )
    result = runtime.list_search_hit_table_rows.execute(request)
    items = [SearchHitListItemResponse.from_row(hit) for hit in result.search_hits]
    return SearchHitListResponse(items=items, count=len(items), limit=limit, offset=offset)
