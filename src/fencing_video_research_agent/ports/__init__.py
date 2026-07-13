"""Application port contracts."""

from fencing_video_research_agent.ports.clock import Clock
from fencing_video_research_agent.ports.repositories import (
    AnnotationRepository,
    CollectionRepository,
    CollectionRunNotFoundError,
    CollectionRunRecordId,
    IncompleteVideoRecordError,
    RepositoryError,
    SearchQueryRecordId,
    VideoNotFoundError,
    VideoRecordId,
    VideoRepository,
)
from fencing_video_research_agent.ports.unit_of_work import UnitOfWork
from fencing_video_research_agent.ports.youtube import (
    PermanentYouTubeGatewayError,
    TransientYouTubeGatewayError,
    YouTubeGateway,
    YouTubeGatewayError,
    YouTubeSearchRequest,
    YouTubeSearchResult,
)

__all__ = [
    "AnnotationRepository",
    "Clock",
    "CollectionRepository",
    "CollectionRunNotFoundError",
    "CollectionRunRecordId",
    "IncompleteVideoRecordError",
    "PermanentYouTubeGatewayError",
    "RepositoryError",
    "SearchQueryRecordId",
    "TransientYouTubeGatewayError",
    "UnitOfWork",
    "VideoNotFoundError",
    "VideoRecordId",
    "VideoRepository",
    "YouTubeGateway",
    "YouTubeGatewayError",
    "YouTubeSearchRequest",
    "YouTubeSearchResult",
]
