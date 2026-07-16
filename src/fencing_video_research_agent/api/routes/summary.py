"""Dashboard summary routes for the API."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from fencing_video_research_agent.api.dependencies import get_api_runtime
from fencing_video_research_agent.api.schemas import SummaryResponse
from fencing_video_research_agent.application.inspect_storage import GetStoredDataSummaryRequest
from fencing_video_research_agent.bootstrap import ApiRuntime

router = APIRouter(prefix="/api", tags=["summary"])


@router.get("/summary", response_model=SummaryResponse)
def get_summary(
    runtime: Annotated[ApiRuntime, Depends(get_api_runtime)],
) -> SummaryResponse:
    """Return dashboard-oriented stored-data counts."""

    result = runtime.summary.execute(GetStoredDataSummaryRequest())
    return SummaryResponse.from_summary(result.summary)
