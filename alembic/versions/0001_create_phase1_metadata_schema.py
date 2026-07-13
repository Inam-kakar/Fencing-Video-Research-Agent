"""Create Phase 1 metadata schema."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the Phase 1 metadata persistence tables."""

    op.create_table(
        "videos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("youtube_video_id", sa.String(length=32), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_videos"),
        sa.UniqueConstraint("youtube_video_id", name="uq_videos_youtube_video_id"),
    )
    op.create_index("ix_videos_first_seen_at", "videos", ["first_seen_at"])
    op.create_index("ix_videos_youtube_video_id", "videos", ["youtube_video_id"])

    op.create_table(
        "search_queries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("query_text", sa.String(length=500), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("parameters_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_search_queries"),
        sa.UniqueConstraint(
            "query_text",
            "parameters_fingerprint",
            name="uq_search_queries_query_text_parameters_fingerprint",
        ),
    )
    op.create_index("ix_search_queries_query_text", "search_queries", ["query_text"])

    op.create_table(
        "youtube_video_metadata",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("video_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("channel_id", sa.String(length=128), nullable=False),
        sa.Column("channel_title", sa.String(length=255), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("view_count", sa.Integer(), nullable=True),
        sa.Column("like_count", sa.Integer(), nullable=True),
        sa.Column("comment_count", sa.Integer(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("thumbnail_url", sa.Text(), nullable=True),
        sa.Column("video_url", sa.Text(), nullable=True),
        sa.Column("last_refreshed_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "comment_count IS NULL OR comment_count >= 0",
            name="ck_youtube_video_metadata_comment_count_non_negative",
        ),
        sa.CheckConstraint(
            "duration_seconds IS NULL OR duration_seconds >= 0",
            name="ck_youtube_video_metadata_duration_seconds_non_negative",
        ),
        sa.CheckConstraint(
            "like_count IS NULL OR like_count >= 0",
            name="ck_youtube_video_metadata_like_count_non_negative",
        ),
        sa.CheckConstraint(
            "view_count IS NULL OR view_count >= 0",
            name="ck_youtube_video_metadata_view_count_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["video_id"],
            ["videos.id"],
            name="fk_youtube_video_metadata_video_id_videos",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_youtube_video_metadata"),
        sa.UniqueConstraint("video_id", name="uq_youtube_video_metadata_video_id"),
    )
    op.create_index(
        "ix_youtube_video_metadata_channel_id",
        "youtube_video_metadata",
        ["channel_id"],
    )
    op.create_index(
        "ix_youtube_video_metadata_last_refreshed_at",
        "youtube_video_metadata",
        ["last_refreshed_at"],
    )
    op.create_index(
        "ix_youtube_video_metadata_published_at",
        "youtube_video_metadata",
        ["published_at"],
    )

    op.create_table(
        "collection_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("search_query_id", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["search_query_id"],
            ["search_queries.id"],
            name="fk_collection_runs_search_query_id_search_queries",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_collection_runs"),
    )
    op.create_index("ix_collection_runs_search_query_id", "collection_runs", ["search_query_id"])
    op.create_index("ix_collection_runs_started_at", "collection_runs", ["started_at"])

    op.create_table(
        "research_annotations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("video_id", sa.Integer(), nullable=False),
        sa.Column("review_status", sa.String(length=32), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("relevance_label", sa.String(length=100), nullable=True),
        sa.Column("competition_name", sa.String(length=255), nullable=True),
        sa.Column("fencer_names", sa.JSON(), nullable=False),
        sa.Column("weapon_category", sa.String(length=50), nullable=True),
        sa.Column("event_notes", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["video_id"],
            ["videos.id"],
            name="fk_research_annotations_video_id_videos",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_research_annotations"),
        sa.UniqueConstraint("video_id", name="uq_research_annotations_video_id"),
    )
    op.create_index(
        "ix_research_annotations_competition_name",
        "research_annotations",
        ["competition_name"],
    )
    op.create_index(
        "ix_research_annotations_relevance_label",
        "research_annotations",
        ["relevance_label"],
    )
    op.create_index(
        "ix_research_annotations_review_status",
        "research_annotations",
        ["review_status"],
    )
    op.create_index(
        "ix_research_annotations_updated_at",
        "research_annotations",
        ["updated_at"],
    )
    op.create_index(
        "ix_research_annotations_weapon_category",
        "research_annotations",
        ["weapon_category"],
    )

    op.create_table(
        "search_hits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("collection_run_id", sa.Integer(), nullable=False),
        sa.Column("video_id", sa.Integer(), nullable=False),
        sa.Column("discovered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=True),
        sa.CheckConstraint("rank IS NULL OR rank >= 1", name="ck_search_hits_rank_positive"),
        sa.ForeignKeyConstraint(
            ["collection_run_id"],
            ["collection_runs.id"],
            name="fk_search_hits_collection_run_id_collection_runs",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["video_id"],
            ["videos.id"],
            name="fk_search_hits_video_id_videos",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_search_hits"),
        sa.UniqueConstraint("collection_run_id", "video_id", name="uq_search_hits_run_video"),
    )
    op.create_index("ix_search_hits_collection_run_id", "search_hits", ["collection_run_id"])
    op.create_index("ix_search_hits_discovered_at", "search_hits", ["discovered_at"])
    op.create_index("ix_search_hits_video_id", "search_hits", ["video_id"])


def downgrade() -> None:
    """Drop the Phase 1 metadata persistence tables."""

    op.drop_index("ix_search_hits_video_id", table_name="search_hits")
    op.drop_index("ix_search_hits_discovered_at", table_name="search_hits")
    op.drop_index("ix_search_hits_collection_run_id", table_name="search_hits")
    op.drop_table("search_hits")

    op.drop_index("ix_research_annotations_weapon_category", table_name="research_annotations")
    op.drop_index("ix_research_annotations_updated_at", table_name="research_annotations")
    op.drop_index("ix_research_annotations_review_status", table_name="research_annotations")
    op.drop_index("ix_research_annotations_relevance_label", table_name="research_annotations")
    op.drop_index("ix_research_annotations_competition_name", table_name="research_annotations")
    op.drop_table("research_annotations")

    op.drop_index("ix_collection_runs_started_at", table_name="collection_runs")
    op.drop_index("ix_collection_runs_search_query_id", table_name="collection_runs")
    op.drop_table("collection_runs")

    op.drop_index("ix_youtube_video_metadata_published_at", table_name="youtube_video_metadata")
    op.drop_index(
        "ix_youtube_video_metadata_last_refreshed_at",
        table_name="youtube_video_metadata",
    )
    op.drop_index("ix_youtube_video_metadata_channel_id", table_name="youtube_video_metadata")
    op.drop_table("youtube_video_metadata")

    op.drop_index("ix_search_queries_query_text", table_name="search_queries")
    op.drop_table("search_queries")

    op.drop_index("ix_videos_youtube_video_id", table_name="videos")
    op.drop_index("ix_videos_first_seen_at", table_name="videos")
    op.drop_table("videos")
