"""Tests for SQLAlchemy export readers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session, sessionmaker
from tests.infrastructure.persistence.test_repositories import make_video

from fencing_video_research_agent.domain import (
    CollectionRun,
    ResearchAnnotation,
    ReviewStatus,
    SearchQuery,
)
from fencing_video_research_agent.infrastructure.persistence.export_repositories import (
    SqlAlchemySearchHitExportReader,
    SqlAlchemyVideoExportReader,
)
from fencing_video_research_agent.infrastructure.persistence.models import (
    CollectionRunRecord,
    SearchHitRecord,
    SearchQueryRecord,
    VideoRecord,
)
from fencing_video_research_agent.infrastructure.persistence.repositories import (
    SqlAlchemyAnnotationRepository,
    SqlAlchemyCollectionRepository,
    SqlAlchemyVideoRepository,
)
from fencing_video_research_agent.ports import IncompleteVideoRecordError

NOW = datetime(2026, 7, 14, 10, 0, tzinfo=UTC)


def test_export_reader_returns_empty_tuple_for_empty_database(
    session_factory: sessionmaker[Session],
) -> None:
    reader = SqlAlchemyVideoExportReader(session_factory)

    assert reader.read_video_exports() == ()


def test_export_reader_includes_video_without_annotation(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        SqlAlchemyVideoRepository(session).add_or_update(
            make_video(
                youtube_video_id="video-no-annotation",
                first_seen_at=NOW,
                title="Unreviewed video",
            )
        )
        session.commit()

    reader = SqlAlchemyVideoExportReader(session_factory)

    records = reader.read_video_exports()

    assert len(records) == 1
    record = records[0]
    assert record.youtube_video_id == "video-no-annotation"
    assert record.title == "Unreviewed video"
    assert record.review_status is None
    assert record.notes is None
    assert record.relevance_label is None
    assert record.fencer_names == ()
    assert record.discovery_run_count == 0
    assert record.first_collection_run_started_at is None
    assert record.latest_query_text is None


def test_export_reader_includes_annotation_fields(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        SqlAlchemyVideoRepository(session).add_or_update(
            make_video(youtube_video_id="video-annotated", first_seen_at=NOW)
        )
        SqlAlchemyAnnotationRepository(session).save(
            ResearchAnnotation(
                youtube_video_id="video-annotated",
                updated_at=NOW + timedelta(hours=1),
                review_status=ReviewStatus.REVIEWED,
                notes="Useful sabre reference.",
                relevance_label="relevant",
                competition_name="European Championship",
                fencer_names=("Fencer One", "Fencer Two"),
                weapon_category="sabre",
                event_notes="Final bout",
            )
        )
        session.commit()

    reader = SqlAlchemyVideoExportReader(session_factory)

    record = reader.read_video_exports()[0]

    assert record.review_status == "reviewed"
    assert record.notes == "Useful sabre reference."
    assert record.relevance_label == "relevant"
    assert record.competition_name == "European Championship"
    assert record.fencer_names == ("Fencer One", "Fencer Two")
    assert record.weapon_category == "sabre"
    assert record.event_notes == "Final bout"
    assert record.annotation_updated_at == NOW + timedelta(hours=1)


def test_export_reader_summarizes_multiple_collection_runs(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        SqlAlchemyVideoRepository(session).add_or_update(
            make_video(youtube_video_id="video-provenance", first_seen_at=NOW)
        )
        collections = SqlAlchemyCollectionRepository(session)
        first_run_id = collections.add_collection_run(
            CollectionRun(
                search_query=SearchQuery("first sabre query", parameters={"order": "date"}),
                started_at=NOW,
                completed_at=NOW + timedelta(minutes=1),
            ),
            status="completed",
        )
        latest_run_id = collections.add_collection_run(
            CollectionRun(
                search_query=SearchQuery("latest sabre query", parameters={"order": "relevance"}),
                started_at=NOW + timedelta(days=1),
                completed_at=NOW + timedelta(days=1, minutes=1),
            ),
            status="completed",
        )
        collections.add_search_hit(
            latest_run_id,
            youtube_video_id="video-provenance",
            discovered_at=NOW + timedelta(days=1),
            rank=2,
        )
        collections.add_search_hit(
            first_run_id,
            youtube_video_id="video-provenance",
            discovered_at=NOW,
            rank=1,
        )
        session.commit()

    reader = SqlAlchemyVideoExportReader(session_factory)

    record = reader.read_video_exports()[0]

    assert record.discovery_run_count == 2
    assert record.first_collection_run_started_at == NOW
    assert record.latest_collection_run_started_at == NOW + timedelta(days=1)
    assert record.first_query_text == "first sabre query"
    assert record.latest_query_text == "latest sabre query"


def test_export_reader_orders_videos_by_first_seen_then_youtube_id(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        videos = SqlAlchemyVideoRepository(session)
        videos.add_or_update(make_video(youtube_video_id="video-b", first_seen_at=NOW, title="B"))
        videos.add_or_update(make_video(youtube_video_id="video-a", first_seen_at=NOW, title="A"))
        videos.add_or_update(
            make_video(
                youtube_video_id="video-c",
                first_seen_at=NOW + timedelta(hours=1),
                title="C",
            )
        )
        session.commit()

    reader = SqlAlchemyVideoExportReader(session_factory)

    records = reader.read_video_exports()

    assert [record.youtube_video_id for record in records] == [
        "video-a",
        "video-b",
        "video-c",
    ]


def test_search_hit_export_reader_returns_empty_tuple_for_empty_database(
    session_factory: sessionmaker[Session],
) -> None:
    reader = SqlAlchemySearchHitExportReader(session_factory)

    assert reader.read_search_hit_exports() == ()


def test_search_hit_export_reader_includes_provenance_video_and_annotation_fields(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        SqlAlchemyVideoRepository(session).add_or_update(
            make_video(youtube_video_id="video-hit", first_seen_at=NOW, title="Ranked hit")
        )
        SqlAlchemyAnnotationRepository(session).save(
            ResearchAnnotation(
                youtube_video_id="video-hit",
                updated_at=NOW + timedelta(hours=1),
                review_status=ReviewStatus.REVIEWED,
                notes="Notes should stay out of search-hit export.",
                relevance_label="relevant",
            )
        )
        collections = SqlAlchemyCollectionRepository(session)
        run_id = collections.add_collection_run(
            CollectionRun(
                search_query=SearchQuery(
                    "sabre fencing final",
                    parameters={"order": "relevance", "regionCode": "US"},
                ),
                started_at=NOW,
                completed_at=NOW + timedelta(minutes=1),
            ),
            status="completed",
        )
        collections.add_search_hit(
            run_id,
            youtube_video_id="video-hit",
            discovered_at=NOW + timedelta(seconds=30),
            rank=3,
        )
        session.commit()

    reader = SqlAlchemySearchHitExportReader(session_factory)

    records = reader.read_search_hit_exports()

    assert len(records) == 1
    record = records[0]
    assert record.collection_run_id == int(run_id)
    assert record.query_text == "sabre fencing final"
    assert record.query_parameters == {"order": "relevance", "regionCode": "US"}
    assert record.query_fingerprint
    assert record.run_started_at == NOW
    assert record.run_completed_at == NOW + timedelta(minutes=1)
    assert record.run_status == "completed"
    assert record.run_error_message is None
    assert record.discovered_at == NOW + timedelta(seconds=30)
    assert record.rank == 3
    assert record.youtube_video_id == "video-hit"
    assert record.title == "Ranked hit"
    assert record.channel_id == "channel-123"
    assert record.channel_title == "Fencing Channel"
    assert record.published_at is not None
    assert record.duration_seconds == 720
    assert record.view_count == 100
    assert record.like_count is None
    assert record.comment_count == 5
    assert record.video_url == "https://www.youtube.com/watch?v=video-hit"
    assert record.last_refreshed_at is not None
    assert record.review_status == "reviewed"
    assert record.relevance_label == "relevant"
    assert not hasattr(record, "notes")


def test_search_hit_export_reader_returns_one_row_per_run_for_repeated_video(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        SqlAlchemyVideoRepository(session).add_or_update(
            make_video(youtube_video_id="repeat-video", first_seen_at=NOW)
        )
        collections = SqlAlchemyCollectionRepository(session)
        first_run_id = collections.add_collection_run(
            CollectionRun(
                search_query=SearchQuery("first query", parameters={"order": "date"}),
                started_at=NOW,
                completed_at=NOW + timedelta(minutes=1),
            ),
            status="completed",
        )
        second_run_id = collections.add_collection_run(
            CollectionRun(
                search_query=SearchQuery("second query", parameters={"order": "relevance"}),
                started_at=NOW + timedelta(days=1),
                completed_at=NOW + timedelta(days=1, minutes=1),
            ),
            status="completed",
        )
        collections.add_search_hit(
            first_run_id,
            youtube_video_id="repeat-video",
            discovered_at=NOW,
            rank=1,
        )
        collections.add_search_hit(
            second_run_id,
            youtube_video_id="repeat-video",
            discovered_at=NOW + timedelta(days=1),
            rank=2,
        )
        session.commit()

    reader = SqlAlchemySearchHitExportReader(session_factory)

    records = reader.read_search_hit_exports()

    assert len(records) == 2
    assert [record.youtube_video_id for record in records] == ["repeat-video", "repeat-video"]
    assert [record.collection_run_id for record in records] == [
        int(first_run_id),
        int(second_run_id),
    ]
    assert [record.query_text for record in records] == ["first query", "second query"]
    assert [record.rank for record in records] == [1, 2]


def test_search_hit_export_reader_fails_for_hit_with_missing_video_metadata(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        video = VideoRecord(youtube_video_id="missing-metadata", first_seen_at=NOW)
        query = SearchQueryRecord(
            query_text="missing metadata query",
            parameters={},
            parameters_fingerprint="empty",
            created_at=NOW,
        )
        run = CollectionRunRecord(
            search_query=query,
            started_at=NOW,
            completed_at=NOW,
            status="completed",
        )
        hit = SearchHitRecord(
            collection_run=run,
            video=video,
            discovered_at=NOW,
            rank=1,
        )
        session.add_all([video, query, run, hit])
        session.commit()

    reader = SqlAlchemySearchHitExportReader(session_factory)

    with pytest.raises(IncompleteVideoRecordError, match="missing-metadata"):
        reader.read_search_hit_exports()
