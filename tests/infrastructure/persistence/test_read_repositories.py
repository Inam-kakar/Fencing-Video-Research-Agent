"""Tests for SQLAlchemy read repositories."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session, sessionmaker
from tests.infrastructure.persistence.test_repositories import make_metadata

from fencing_video_research_agent.domain import (
    CollectionRun,
    ResearchAnnotation,
    ReviewStatus,
    SearchQuery,
    Video,
)
from fencing_video_research_agent.infrastructure.persistence.read_repositories import (
    SqlAlchemyStoredDataReader,
)
from fencing_video_research_agent.infrastructure.persistence.repositories import (
    SqlAlchemyAnnotationRepository,
    SqlAlchemyCollectionRepository,
    SqlAlchemyVideoRepository,
)
from fencing_video_research_agent.ports import CollectionRunRecordId

NOW = datetime(2026, 7, 13, 8, 0, tzinfo=UTC)


def make_video(
    youtube_video_id: str,
    *,
    first_seen_at: datetime,
    title: str,
) -> Video:
    """Create a domain video for read-repository tests."""

    return Video(
        youtube_video_id=youtube_video_id,
        first_seen_at=first_seen_at,
        metadata=make_metadata(
            youtube_video_id=youtube_video_id,
            title=title,
            last_refreshed_at=first_seen_at + timedelta(minutes=5),
        ),
    )


def test_reader_lists_videos_newest_first(
    session_factory: sessionmaker[Session],
) -> None:
    """Video summaries are ordered by first-seen time, then YouTube ID."""

    with session_factory() as session:
        videos = SqlAlchemyVideoRepository(session)
        videos.add_or_update(
            make_video("video-b", first_seen_at=NOW + timedelta(hours=1), title="Newer B")
        )
        videos.add_or_update(
            make_video("video-a", first_seen_at=NOW + timedelta(hours=1), title="Newer A")
        )
        videos.add_or_update(make_video("video-c", first_seen_at=NOW, title="Older C"))
        session.commit()

    reader = SqlAlchemyStoredDataReader(session_factory)

    summaries = reader.list_videos(limit=10)

    assert [summary.youtube_video_id for summary in summaries] == [
        "video-a",
        "video-b",
        "video-c",
    ]
    assert summaries[0].title == "Newer A"
    assert summaries[0].last_refreshed_at == NOW + timedelta(hours=1, minutes=5)


def test_reader_respects_list_limit(session_factory: sessionmaker[Session]) -> None:
    """The read repository applies the caller-provided list limit."""

    with session_factory() as session:
        videos = SqlAlchemyVideoRepository(session)
        videos.add_or_update(make_video("video-1", first_seen_at=NOW, title="One"))
        videos.add_or_update(make_video("video-2", first_seen_at=NOW, title="Two"))
        session.commit()

    reader = SqlAlchemyStoredDataReader(session_factory)

    summaries = reader.list_videos(limit=1)

    assert len(summaries) == 1


def test_reader_returns_empty_tuple_for_empty_database(
    session_factory: sessionmaker[Session],
) -> None:
    """An empty migrated database produces an empty read result."""

    reader = SqlAlchemyStoredDataReader(session_factory)

    assert reader.list_videos(limit=20) == ()


def test_reader_returns_video_detail_with_annotation_status(
    session_factory: sessionmaker[Session],
) -> None:
    """Video detail includes YouTube metadata and separate annotation status."""

    with session_factory() as session:
        SqlAlchemyVideoRepository(session).add_or_update(
            make_video("video-123", first_seen_at=NOW, title="Sabre final")
        )
        SqlAlchemyAnnotationRepository(session).save(
            ResearchAnnotation(
                youtube_video_id="video-123",
                updated_at=NOW,
                review_status=ReviewStatus.REVIEWED,
                notes="Useful reference.",
            )
        )
        session.commit()

    reader = SqlAlchemyStoredDataReader(session_factory)

    detail = reader.get_video("video-123")

    assert detail is not None
    assert detail.youtube_video_id == "video-123"
    assert detail.title == "Sabre final"
    assert detail.channel_id == "channel-123"
    assert detail.duration_seconds == 720
    assert detail.tags == ("sabre", "final")
    assert detail.annotation_status == "reviewed"


def test_reader_returns_none_for_missing_video(
    session_factory: sessionmaker[Session],
) -> None:
    """Missing videos are represented without raising from the reader."""

    reader = SqlAlchemyStoredDataReader(session_factory)

    assert reader.get_video("missing-video") is None


def test_reader_lists_collection_runs_newest_first(
    session_factory: sessionmaker[Session],
) -> None:
    """Collection-run summaries are ordered by started time, then run ID."""

    with session_factory() as session:
        videos = SqlAlchemyVideoRepository(session)
        videos.add_or_update(make_video("video-1", first_seen_at=NOW, title="One"))
        collections = SqlAlchemyCollectionRepository(session)
        older_run_id = collections.add_collection_run(
            CollectionRun(
                search_query=SearchQuery("older sabre", parameters={"order": "date"}),
                started_at=NOW,
                completed_at=NOW,
            ),
            status="completed",
        )
        newer_first_id = collections.add_collection_run(
            CollectionRun(
                search_query=SearchQuery("newer sabre one", parameters={"order": "date"}),
                started_at=NOW + timedelta(hours=1),
                completed_at=NOW + timedelta(hours=1),
            ),
            status="completed",
        )
        newer_second_id = collections.add_collection_run(
            CollectionRun(
                search_query=SearchQuery("newer sabre two", parameters={"order": "date"}),
                started_at=NOW + timedelta(hours=1),
                completed_at=NOW + timedelta(hours=1),
            ),
            status="completed",
        )
        collections.add_search_hit(
            older_run_id,
            youtube_video_id="video-1",
            discovered_at=NOW,
            rank=1,
        )
        session.commit()

    reader = SqlAlchemyStoredDataReader(session_factory)

    summaries = reader.list_collection_runs(limit=10)

    assert [summary.run_id for summary in summaries] == [
        newer_second_id,
        newer_first_id,
        older_run_id,
    ]
    assert summaries[-1].query_text == "older sabre"
    assert summaries[-1].hit_count == 1


def test_reader_respects_collection_run_list_limit(
    session_factory: sessionmaker[Session],
) -> None:
    """The collection-run reader applies the caller-provided list limit."""

    with session_factory() as session:
        collections = SqlAlchemyCollectionRepository(session)
        collections.add_collection_run(
            CollectionRun(search_query=SearchQuery("one"), started_at=NOW),
            status="completed",
        )
        collections.add_collection_run(
            CollectionRun(search_query=SearchQuery("two"), started_at=NOW + timedelta(hours=1)),
            status="completed",
        )
        session.commit()

    reader = SqlAlchemyStoredDataReader(session_factory)

    summaries = reader.list_collection_runs(limit=1)

    assert len(summaries) == 1


def test_reader_returns_empty_tuple_for_no_collection_runs(
    session_factory: sessionmaker[Session],
) -> None:
    """An empty migrated database has no collection runs to inspect."""

    reader = SqlAlchemyStoredDataReader(session_factory)

    assert reader.list_collection_runs(limit=20) == ()


def test_reader_returns_collection_run_detail_with_ranked_hits(
    session_factory: sessionmaker[Session],
) -> None:
    """Run detail includes query provenance and hit videos in stable rank order."""

    with session_factory() as session:
        videos = SqlAlchemyVideoRepository(session)
        videos.add_or_update(make_video("video-b", first_seen_at=NOW, title="Rank missing"))
        videos.add_or_update(make_video("video-c", first_seen_at=NOW, title="Rank two"))
        videos.add_or_update(make_video("video-a", first_seen_at=NOW, title="Rank one"))
        collections = SqlAlchemyCollectionRepository(session)
        run_id = collections.add_collection_run(
            CollectionRun(
                search_query=SearchQuery(
                    "world cup sabre",
                    parameters={"order": "date", "max_results": 3},
                ),
                started_at=NOW,
                completed_at=NOW + timedelta(minutes=1),
            ),
            status="completed",
        )
        collections.add_search_hit(
            run_id,
            youtube_video_id="video-b",
            discovered_at=NOW,
            rank=None,
        )
        collections.add_search_hit(
            run_id,
            youtube_video_id="video-c",
            discovered_at=NOW,
            rank=2,
        )
        collections.add_search_hit(
            run_id,
            youtube_video_id="video-a",
            discovered_at=NOW,
            rank=1,
        )
        session.commit()

    reader = SqlAlchemyStoredDataReader(session_factory)

    detail = reader.get_collection_run(run_id)

    assert detail is not None
    assert detail.run_id == run_id
    assert detail.query_text == "world cup sabre"
    assert dict(detail.query_parameters) == {"order": "date", "max_results": 3}
    assert detail.status == "completed"
    assert detail.hit_count == 3
    assert [(hit.rank, hit.youtube_video_id, hit.title) for hit in detail.hits] == [
        (1, "video-a", "Rank one"),
        (2, "video-c", "Rank two"),
        (None, "video-b", "Rank missing"),
    ]


def test_reader_returns_none_for_missing_collection_run(
    session_factory: sessionmaker[Session],
) -> None:
    """Missing collection runs are represented without raising from the reader."""

    reader = SqlAlchemyStoredDataReader(session_factory)

    assert reader.get_collection_run(CollectionRunRecordId(999)) is None
