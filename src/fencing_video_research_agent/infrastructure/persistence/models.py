"""SQLAlchemy table mappings for Phase 1 metadata persistence."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from fencing_video_research_agent.infrastructure.persistence.types import UTCDateTime

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Base class for SQLAlchemy ORM mappings."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class VideoRecord(Base):
    """Stored public YouTube video identity and discovery timestamp."""

    __tablename__ = "videos"
    __table_args__ = (
        UniqueConstraint("youtube_video_id", name="uq_videos_youtube_video_id"),
        Index("ix_videos_youtube_video_id", "youtube_video_id"),
        Index("ix_videos_first_seen_at", "first_seen_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    youtube_video_id: Mapped[str] = mapped_column(String(32), nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)

    youtube_metadata: Mapped[YouTubeVideoMetadataRecord | None] = relationship(
        back_populates="video",
        cascade="all, delete-orphan",
        uselist=False,
    )
    search_hits: Mapped[list[SearchHitRecord]] = relationship(back_populates="video")
    annotation: Mapped[ResearchAnnotationRecord | None] = relationship(
        back_populates="video",
        cascade="all, delete-orphan",
        uselist=False,
    )


class YouTubeVideoMetadataRecord(Base):
    """Latest YouTube-owned metadata for one stored video."""

    __tablename__ = "youtube_video_metadata"
    __table_args__ = (
        UniqueConstraint("video_id", name="uq_youtube_video_metadata_video_id"),
        CheckConstraint(
            "duration_seconds IS NULL OR duration_seconds >= 0",
            name="duration_seconds_non_negative",
        ),
        CheckConstraint(
            "view_count IS NULL OR view_count >= 0",
            name="view_count_non_negative",
        ),
        CheckConstraint(
            "like_count IS NULL OR like_count >= 0",
            name="like_count_non_negative",
        ),
        CheckConstraint(
            "comment_count IS NULL OR comment_count >= 0",
            name="comment_count_non_negative",
        ),
        Index("ix_youtube_video_metadata_channel_id", "channel_id"),
        Index("ix_youtube_video_metadata_published_at", "published_at"),
        Index("ix_youtube_video_metadata_last_refreshed_at", "last_refreshed_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    video_id: Mapped[int] = mapped_column(
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    channel_id: Mapped[str] = mapped_column(String(128), nullable=False)
    channel_title: Mapped[str] = mapped_column(String(255), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    view_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    like_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    comment_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    thumbnail_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    video_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_refreshed_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)

    video: Mapped[VideoRecord] = relationship(back_populates="youtube_metadata")


class SearchQueryRecord(Base):
    """A YouTube search term and the parameters used for discovery."""

    __tablename__ = "search_queries"
    __table_args__ = (
        UniqueConstraint(
            "query_text",
            "parameters_fingerprint",
            name="uq_search_queries_query_text_parameters_fingerprint",
        ),
        Index("ix_search_queries_query_text", "query_text"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    query_text: Mapped[str] = mapped_column(String(500), nullable=False)
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    parameters_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)

    collection_runs: Mapped[list[CollectionRunRecord]] = relationship(
        back_populates="search_query",
        cascade="all, delete-orphan",
    )


class CollectionRunRecord(Base):
    """A single collection attempt for one stored search query."""

    __tablename__ = "collection_runs"
    __table_args__ = (
        Index("ix_collection_runs_search_query_id", "search_query_id"),
        Index("ix_collection_runs_started_at", "started_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    search_query_id: Mapped[int] = mapped_column(
        ForeignKey("search_queries.id", ondelete="CASCADE"),
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    search_query: Mapped[SearchQueryRecord] = relationship(back_populates="collection_runs")
    search_hits: Mapped[list[SearchHitRecord]] = relationship(
        back_populates="collection_run",
        cascade="all, delete-orphan",
    )


class SearchHitRecord(Base):
    """The fact that a collection run returned a stored video."""

    __tablename__ = "search_hits"
    __table_args__ = (
        UniqueConstraint("collection_run_id", "video_id", name="uq_search_hits_run_video"),
        CheckConstraint("rank IS NULL OR rank >= 1", name="rank_positive"),
        Index("ix_search_hits_collection_run_id", "collection_run_id"),
        Index("ix_search_hits_video_id", "video_id"),
        Index("ix_search_hits_discovered_at", "discovered_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    collection_run_id: Mapped[int] = mapped_column(
        ForeignKey("collection_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    video_id: Mapped[int] = mapped_column(
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False,
    )
    discovered_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)

    collection_run: Mapped[CollectionRunRecord] = relationship(back_populates="search_hits")
    video: Mapped[VideoRecord] = relationship(back_populates="search_hits")


class ResearchAnnotationRecord(Base):
    """Researcher-owned review fields kept separate from YouTube metadata."""

    __tablename__ = "research_annotations"
    __table_args__ = (
        UniqueConstraint("video_id", name="uq_research_annotations_video_id"),
        Index("ix_research_annotations_review_status", "review_status"),
        Index("ix_research_annotations_relevance_label", "relevance_label"),
        Index("ix_research_annotations_competition_name", "competition_name"),
        Index("ix_research_annotations_weapon_category", "weapon_category"),
        Index("ix_research_annotations_updated_at", "updated_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    video_id: Mapped[int] = mapped_column(
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False,
    )
    review_status: Mapped[str] = mapped_column(String(32), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    relevance_label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    competition_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    fencer_names: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    weapon_category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    event_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)

    video: Mapped[VideoRecord] = relationship(back_populates="annotation")
