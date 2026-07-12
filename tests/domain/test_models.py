"""Tests for framework-free domain models."""

from datetime import UTC, datetime, timedelta

import pytest

from fencing_video_research_agent.domain import (
    CollectionRun,
    ResearchAnnotation,
    ReviewStatus,
    SearchHit,
    SearchQuery,
    Video,
    YouTubeMetadata,
)

NOW = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)


def make_metadata(
    *,
    youtube_video_id: str = "video-123",
    title: str = "Sabre final",
    last_refreshed_at: datetime = NOW,
) -> YouTubeMetadata:
    """Create valid metadata for focused domain tests."""

    return YouTubeMetadata(
        youtube_video_id=youtube_video_id,
        title=title,
        description=None,
        channel_id="channel-123",
        channel_title="Fencing Channel",
        published_at=NOW - timedelta(days=1),
        duration=timedelta(minutes=12),
        view_count=100,
        like_count=None,
        comment_count=None,
        last_refreshed_at=last_refreshed_at,
        tags=("sabre", "final"),
        thumbnail_url=None,
        video_url="https://www.youtube.com/watch?v=video-123",
    )


def test_video_refresh_preserves_first_seen_timestamp() -> None:
    first_seen_at = NOW - timedelta(hours=2)
    video = Video(
        youtube_video_id="video-123",
        first_seen_at=first_seen_at,
        metadata=make_metadata(title="Original title"),
    )

    refreshed = video.with_refreshed_metadata(make_metadata(title="Updated title"))

    assert refreshed.first_seen_at == first_seen_at
    assert refreshed.metadata.title == "Updated title"
    assert video.metadata.title == "Original title"


def test_metadata_requires_utc_timestamps() -> None:
    naive_time = datetime(2026, 1, 2, 3, 4, 5)

    with pytest.raises(ValueError, match="last_refreshed_at"):
        make_metadata(last_refreshed_at=naive_time)


def test_search_query_copies_parameters() -> None:
    parameters = {"order": "relevance", "max_results": 25}

    query = SearchQuery(query_text="sabre fencing", parameters=parameters)
    parameters["order"] = "date"

    assert query.query_text == "sabre fencing"
    assert query.parameters["order"] == "relevance"
    assert query.parameters["max_results"] == 25


def test_search_hit_records_query_video_relationship() -> None:
    query = SearchQuery(query_text="world cup sabre")

    hit = SearchHit(
        query=query,
        youtube_video_id="video-123",
        discovered_at=NOW,
        rank=1,
    )

    assert hit.query == query
    assert hit.youtube_video_id == "video-123"
    assert hit.rank == 1


def test_collection_run_rejects_completion_before_start() -> None:
    query = SearchQuery(query_text="olympic sabre")

    with pytest.raises(ValueError, match="completed_at"):
        CollectionRun(
            search_query=query,
            started_at=NOW,
            completed_at=NOW - timedelta(seconds=1),
        )


def test_annotation_is_research_owned_and_defaults_to_unreviewed() -> None:
    annotation = ResearchAnnotation(
        youtube_video_id="video-123",
        updated_at=NOW,
        notes="Likely sabre bout.",
        fencer_names=("Fencer One", "Fencer Two"),
    )

    assert annotation.review_status is ReviewStatus.UNREVIEWED
    assert annotation.notes == "Likely sabre bout."
    assert annotation.fencer_names == ("Fencer One", "Fencer Two")
