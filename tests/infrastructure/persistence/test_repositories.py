"""Tests for SQLAlchemy repository implementations."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from fencing_video_research_agent.domain import (
    CollectionRun,
    ResearchAnnotation,
    ReviewStatus,
    SearchQuery,
    Video,
    YouTubeMetadata,
)
from fencing_video_research_agent.infrastructure.persistence.models import (
    CollectionRunRecord,
    ResearchAnnotationRecord,
    SearchHitRecord,
    SearchQueryRecord,
    VideoRecord,
    YouTubeVideoMetadataRecord,
)
from fencing_video_research_agent.infrastructure.persistence.repositories import (
    SqlAlchemyAnnotationRepository,
    SqlAlchemyCollectionRepository,
    SqlAlchemyVideoRepository,
)
from fencing_video_research_agent.ports import (
    CollectionRunNotFoundError,
    CollectionRunRecordId,
    VideoNotFoundError,
)

NOW = datetime(2026, 7, 13, 8, 0, tzinfo=UTC)


def make_metadata(
    *,
    youtube_video_id: str = "video-123",
    title: str = "Sabre final",
    last_refreshed_at: datetime = NOW,
) -> YouTubeMetadata:
    """Create valid project-owned metadata for repository tests."""

    return YouTubeMetadata(
        youtube_video_id=youtube_video_id,
        title=title,
        description="A public fencing bout.",
        channel_id="channel-123",
        channel_title="Fencing Channel",
        published_at=NOW - timedelta(days=1),
        duration=timedelta(minutes=12),
        view_count=100,
        like_count=None,
        comment_count=5,
        last_refreshed_at=last_refreshed_at,
        tags=("sabre", "final"),
        thumbnail_url="https://example.com/thumb.jpg",
        video_url=f"https://www.youtube.com/watch?v={youtube_video_id}",
    )


def make_video(
    *,
    youtube_video_id: str = "video-123",
    first_seen_at: datetime = NOW,
    title: str = "Sabre final",
    last_refreshed_at: datetime = NOW,
) -> Video:
    """Create a valid domain video for repository tests."""

    return Video(
        youtube_video_id=youtube_video_id,
        first_seen_at=first_seen_at,
        metadata=make_metadata(
            youtube_video_id=youtube_video_id,
            title=title,
            last_refreshed_at=last_refreshed_at,
        ),
    )


def test_video_repository_inserts_and_reads_domain_video(
    session_factory: sessionmaker[Session],
) -> None:
    """Video rows and latest metadata map back to framework-free domain models."""

    with session_factory() as session:
        repository = SqlAlchemyVideoRepository(session)
        repository.add_or_update(make_video())
        session.commit()

    with session_factory() as session:
        stored = SqlAlchemyVideoRepository(session).get_by_youtube_id("video-123")

    assert stored is not None
    assert stored.youtube_video_id == "video-123"
    assert stored.first_seen_at == NOW
    assert stored.metadata.title == "Sabre final"
    assert stored.metadata.duration == timedelta(minutes=12)
    assert stored.metadata.tags == ("sabre", "final")


def test_video_repository_reuses_duplicate_youtube_id_and_updates_metadata(
    session_factory: sessionmaker[Session],
) -> None:
    """Duplicate YouTube IDs reuse the video row and preserve first-seen time."""

    first_seen_at = NOW - timedelta(days=5)
    with session_factory() as session:
        repository = SqlAlchemyVideoRepository(session)
        first_id = repository.add_or_update(
            make_video(first_seen_at=first_seen_at, title="Original title")
        )
        second_id = repository.add_or_update(
            make_video(
                first_seen_at=NOW,
                title="Updated title",
                last_refreshed_at=NOW + timedelta(hours=1),
            )
        )
        session.commit()

        stored = repository.get_by_youtube_id("video-123")
        video_count = session.scalar(select(func.count()).select_from(VideoRecord))

    assert first_id == second_id
    assert video_count == 1
    assert stored is not None
    assert stored.first_seen_at == first_seen_at
    assert stored.metadata.title == "Updated title"
    assert stored.metadata.last_refreshed_at == NOW + timedelta(hours=1)


def test_metadata_refresh_does_not_overwrite_research_annotation(
    session_factory: sessionmaker[Session],
) -> None:
    """Updating YouTube metadata leaves researcher-owned annotations intact."""

    with session_factory() as session:
        videos = SqlAlchemyVideoRepository(session)
        annotations = SqlAlchemyAnnotationRepository(session)
        videos.add_or_update(make_video(title="Original title"))
        annotations.save(
            ResearchAnnotation(
                youtube_video_id="video-123",
                updated_at=NOW,
                review_status=ReviewStatus.REVIEWED,
                notes="Important sabre reference.",
                relevance_label="relevant",
                fencer_names=("Fencer One",),
            )
        )

        videos.add_or_update(make_video(title="Refreshed title"))
        session.commit()

        stored_video = videos.get_by_youtube_id("video-123")
        stored_annotation = annotations.get_by_youtube_id("video-123")

    assert stored_video is not None
    assert stored_video.metadata.title == "Refreshed title"
    assert stored_annotation is not None
    assert stored_annotation.notes == "Important sabre reference."
    assert stored_annotation.review_status is ReviewStatus.REVIEWED
    assert stored_annotation.fencer_names == ("Fencer One",)


def test_search_query_get_or_create_uses_parameter_fingerprint(
    session_factory: sessionmaker[Session],
) -> None:
    """Search queries are unique by query text and canonical parameter fingerprint."""

    query = SearchQuery(
        query_text="sabre fencing",
        parameters={"order": "relevance", "max_results": 25},
    )
    same_query = SearchQuery(
        query_text="sabre fencing",
        parameters={"max_results": 25, "order": "relevance"},
    )
    different_query = SearchQuery(
        query_text="sabre fencing",
        parameters={"order": "date", "max_results": 25},
    )

    with session_factory() as session:
        repository = SqlAlchemyCollectionRepository(session)
        first_id = repository.get_or_create_search_query(query, created_at=NOW)
        same_id = repository.get_or_create_search_query(same_query, created_at=NOW)
        different_id = repository.get_or_create_search_query(different_query, created_at=NOW)
        session.commit()

        query_count = session.scalar(select(func.count()).select_from(SearchQueryRecord))

    assert first_id == same_id
    assert different_id != first_id
    assert query_count == 2


def test_collection_run_and_search_hit_preserve_relationship_path(
    session_factory: sessionmaker[Session],
) -> None:
    """Search hits link collection runs to videos without duplicating query IDs."""

    search_query = SearchQuery(query_text="world cup sabre", parameters={"order": "date"})
    run = CollectionRun(search_query=search_query, started_at=NOW, completed_at=NOW)

    with session_factory() as session:
        SqlAlchemyVideoRepository(session).add_or_update(make_video())
        collections = SqlAlchemyCollectionRepository(session)
        run_id = collections.add_collection_run(run, status="completed")
        collections.add_search_hit(
            run_id,
            youtube_video_id="video-123",
            discovered_at=NOW,
            rank=1,
        )
        collections.add_search_hit(
            run_id,
            youtube_video_id="video-123",
            discovered_at=NOW,
            rank=1,
        )
        session.commit()

        hit_count = session.scalar(select(func.count()).select_from(SearchHitRecord))
        hit = session.scalars(select(SearchHitRecord)).one()
        assert not hasattr(SearchHitRecord, "search_query_id")
        assert hit.collection_run.search_query.query_text == "world cup sabre"
        assert hit.video.youtube_video_id == "video-123"

    assert hit_count == 1


def test_collection_repository_reports_missing_run_and_video(
    session_factory: sessionmaker[Session],
) -> None:
    """Search hits require both an existing collection run and stored video."""

    run = CollectionRun(search_query=SearchQuery("sabre fencing"), started_at=NOW)

    with session_factory() as session:
        repository = SqlAlchemyCollectionRepository(session)

        with pytest.raises(CollectionRunNotFoundError):
            repository.add_search_hit(
                CollectionRunRecordId(999),
                youtube_video_id="missing-video",
                discovered_at=NOW,
            )

        run_id = repository.add_collection_run(run, status="completed")
        with pytest.raises(VideoNotFoundError):
            repository.add_search_hit(
                run_id,
                youtube_video_id="missing-video",
                discovered_at=NOW,
            )


def test_annotation_repository_requires_existing_video(
    session_factory: sessionmaker[Session],
) -> None:
    """Annotations cannot be saved for unknown videos."""

    annotation = ResearchAnnotation(youtube_video_id="missing-video", updated_at=NOW)

    with session_factory() as session:
        with pytest.raises(VideoNotFoundError):
            SqlAlchemyAnnotationRepository(session).save(annotation)


def test_repository_rows_use_expected_tables(
    session_factory: sessionmaker[Session],
) -> None:
    """Repository operations write only the approved Phase 1 persistence tables."""

    with session_factory() as session:
        videos = SqlAlchemyVideoRepository(session)
        annotations = SqlAlchemyAnnotationRepository(session)
        videos.add_or_update(make_video())
        annotations.save(ResearchAnnotation(youtube_video_id="video-123", updated_at=NOW))
        session.commit()

        assert session.scalar(select(func.count()).select_from(VideoRecord)) == 1
        assert session.scalar(select(func.count()).select_from(YouTubeVideoMetadataRecord)) == 1
        assert session.scalar(select(func.count()).select_from(ResearchAnnotationRecord)) == 1
        assert session.scalar(select(func.count()).select_from(CollectionRunRecord)) == 0
