"""Pydantic schemas for the FastAPI interface."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, model_validator

from fencing_video_research_agent.domain import ResearchAnnotation
from fencing_video_research_agent.ports.stored_data import (
    StoredCollectionRunDetail,
    StoredCollectionRunHit,
    StoredCollectionRunSummary,
    StoredDataSummary,
    StoredSearchHitTableRow,
    StoredVideoDetail,
    StoredVideoTableRow,
)


class HealthResponse(BaseModel):
    """Health-check response."""

    status: str


class SummaryResponse(BaseModel):
    """Dashboard summary counts."""

    video_count: int
    collection_run_count: int
    search_hit_count: int
    annotation_count: int
    reviewed_count: int
    unreviewed_count: int

    @classmethod
    def from_summary(cls, summary: StoredDataSummary) -> Self:
        """Create a response from a stored-data summary DTO."""

        return cls(
            video_count=summary.video_count,
            collection_run_count=summary.collection_run_count,
            search_hit_count=summary.search_hit_count,
            annotation_count=summary.annotation_count,
            reviewed_count=summary.reviewed_count,
            unreviewed_count=summary.unreviewed_count,
        )


class VideoListItemResponse(BaseModel):
    """One stored video row for frontend table views."""

    youtube_video_id: str
    title: str
    channel_title: str
    duration_seconds: int | None
    published_at: datetime | None
    view_count: int | None
    review_status: str | None
    relevance_label: str | None
    video_url: str | None
    first_seen_at: datetime
    last_refreshed_at: datetime

    @classmethod
    def from_row(cls, row: StoredVideoTableRow) -> Self:
        """Create a response from a stored-video table row."""

        return cls(
            youtube_video_id=row.youtube_video_id,
            title=row.title,
            channel_title=row.channel_title,
            duration_seconds=row.duration_seconds,
            published_at=row.published_at,
            view_count=row.view_count,
            review_status=row.review_status,
            relevance_label=row.relevance_label,
            video_url=row.video_url,
            first_seen_at=row.first_seen_at,
            last_refreshed_at=row.last_refreshed_at,
        )


class VideoListResponse(BaseModel):
    """Paginated stored-video table response."""

    items: list[VideoListItemResponse]
    count: int
    limit: int
    offset: int


class VideoDetailResponse(BaseModel):
    """Detailed stored video response."""

    youtube_video_id: str
    title: str
    description: str | None
    channel_id: str
    channel_title: str
    published_at: datetime | None
    duration_seconds: int | None
    view_count: int | None
    like_count: int | None
    comment_count: int | None
    tags: tuple[str, ...]
    thumbnail_url: str | None
    video_url: str | None
    first_seen_at: datetime
    last_refreshed_at: datetime
    review_status: str | None
    notes: str | None
    relevance_label: str | None
    competition_name: str | None
    fencer_names: tuple[str, ...]
    weapon_category: str | None
    event_notes: str | None
    annotation_updated_at: datetime | None
    discovery_run_count: int
    first_collection_run_started_at: datetime | None
    latest_collection_run_started_at: datetime | None
    first_query_text: str | None
    latest_query_text: str | None

    @classmethod
    def from_detail(cls, detail: StoredVideoDetail) -> Self:
        """Create a response from a stored-video detail DTO."""

        return cls(
            youtube_video_id=detail.youtube_video_id,
            title=detail.title,
            description=detail.description,
            channel_id=detail.channel_id,
            channel_title=detail.channel_title,
            published_at=detail.published_at,
            duration_seconds=detail.duration_seconds,
            view_count=detail.view_count,
            like_count=detail.like_count,
            comment_count=detail.comment_count,
            tags=detail.tags,
            thumbnail_url=detail.thumbnail_url,
            video_url=detail.video_url,
            first_seen_at=detail.first_seen_at,
            last_refreshed_at=detail.last_refreshed_at,
            review_status=detail.annotation_status,
            notes=detail.notes,
            relevance_label=detail.relevance_label,
            competition_name=detail.competition_name,
            fencer_names=detail.fencer_names,
            weapon_category=detail.weapon_category,
            event_notes=detail.event_notes,
            annotation_updated_at=detail.annotation_updated_at,
            discovery_run_count=detail.discovery_run_count,
            first_collection_run_started_at=detail.first_collection_run_started_at,
            latest_collection_run_started_at=detail.latest_collection_run_started_at,
            first_query_text=detail.first_query_text,
            latest_query_text=detail.latest_query_text,
        )


class UpdateVideoAnnotationRequest(BaseModel):
    """Request body for browser-editable annotation fields."""

    model_config = ConfigDict(extra="forbid")

    review_status: Literal["unreviewed", "reviewed"] | None = None
    relevance_label: str | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def validate_update_fields(self) -> Self:
        """Require at least one supplied field and a non-null review status."""

        provided_fields = {"review_status", "relevance_label", "notes"} & self.model_fields_set
        if not provided_fields:
            msg = "at least one annotation field must be provided"
            raise ValueError(msg)
        if "review_status" in self.model_fields_set and self.review_status is None:
            msg = "review_status must be unreviewed or reviewed"
            raise ValueError(msg)
        return self


class VideoAnnotationResponse(BaseModel):
    """Updated annotation summary for one stored video."""

    youtube_video_id: str
    review_status: str
    relevance_label: str | None
    notes: str | None
    updated_at: datetime

    @classmethod
    def from_annotation(cls, annotation: ResearchAnnotation) -> Self:
        """Create a response from a domain annotation."""

        return cls(
            youtube_video_id=annotation.youtube_video_id,
            review_status=annotation.review_status.value,
            relevance_label=annotation.relevance_label,
            notes=annotation.notes,
            updated_at=annotation.updated_at,
        )


class RunListItemResponse(BaseModel):
    """One collection-run row for frontend table views."""

    run_id: int
    query_text: str
    status: str
    started_at: datetime
    completed_at: datetime | None
    hit_count: int

    @classmethod
    def from_row(cls, row: StoredCollectionRunSummary) -> Self:
        """Create a response from a collection-run summary DTO."""

        return cls(
            run_id=int(row.run_id),
            query_text=row.query_text,
            status=row.status,
            started_at=row.started_at,
            completed_at=row.completed_at,
            hit_count=row.hit_count,
        )


class RunListResponse(BaseModel):
    """Paginated collection-run table response."""

    items: list[RunListItemResponse]
    count: int
    limit: int
    offset: int


class RunHitResponse(BaseModel):
    """One returned video in a collection-run detail response."""

    rank: int | None
    youtube_video_id: str
    title: str
    channel_title: str

    @classmethod
    def from_hit(cls, hit: StoredCollectionRunHit) -> Self:
        """Create a response from a collection-run hit DTO."""

        return cls(
            rank=hit.rank,
            youtube_video_id=hit.youtube_video_id,
            title=hit.title,
            channel_title=hit.channel_title,
        )


class RunDetailResponse(BaseModel):
    """Detailed collection-run response."""

    run_id: int
    query_text: str
    query_parameters: dict[str, object]
    status: str
    started_at: datetime
    completed_at: datetime | None
    hit_count: int
    hits: list[RunHitResponse]

    @classmethod
    def from_detail(cls, detail: StoredCollectionRunDetail) -> Self:
        """Create a response from a collection-run detail DTO."""

        return cls(
            run_id=int(detail.run_id),
            query_text=detail.query_text,
            query_parameters=dict(detail.query_parameters),
            status=detail.status,
            started_at=detail.started_at,
            completed_at=detail.completed_at,
            hit_count=detail.hit_count,
            hits=[RunHitResponse.from_hit(hit) for hit in detail.hits],
        )


class SearchHitListItemResponse(BaseModel):
    """One search-hit provenance row for frontend table views."""

    collection_run_id: int
    query_text: str
    run_started_at: datetime
    rank: int | None
    discovered_at: datetime
    youtube_video_id: str
    title: str
    channel_title: str
    review_status: str | None
    relevance_label: str | None

    @classmethod
    def from_row(cls, row: StoredSearchHitTableRow) -> Self:
        """Create a response from a search-hit table row."""

        return cls(
            collection_run_id=int(row.collection_run_id),
            query_text=row.query_text,
            run_started_at=row.run_started_at,
            rank=row.rank,
            discovered_at=row.discovered_at,
            youtube_video_id=row.youtube_video_id,
            title=row.title,
            channel_title=row.channel_title,
            review_status=row.review_status,
            relevance_label=row.relevance_label,
        )


class SearchHitListResponse(BaseModel):
    """Paginated search-hit provenance table response."""

    items: list[SearchHitListItemResponse]
    count: int
    limit: int
    offset: int
