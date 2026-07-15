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


def test_reader_returns_dashboard_summary_counts(
    session_factory: sessionmaker[Session],
) -> None:
    """Dashboard summary counts treat unannotated videos as unreviewed."""

    with session_factory() as session:
        videos = SqlAlchemyVideoRepository(session)
        videos.add_or_update(make_video("reviewed-video", first_seen_at=NOW, title="Reviewed"))
        videos.add_or_update(make_video("unreviewed-video", first_seen_at=NOW, title="Unreviewed"))
        SqlAlchemyAnnotationRepository(session).save(
            ResearchAnnotation(
                youtube_video_id="reviewed-video",
                updated_at=NOW,
                review_status=ReviewStatus.REVIEWED,
            )
        )
        collections = SqlAlchemyCollectionRepository(session)
        run_id = collections.add_collection_run(
            CollectionRun(search_query=SearchQuery("sabre"), started_at=NOW),
            status="completed",
        )
        collections.add_search_hit(
            run_id,
            youtube_video_id="reviewed-video",
            discovered_at=NOW,
            rank=1,
        )
        session.commit()

    reader = SqlAlchemyStoredDataReader(session_factory)

    summary = reader.get_summary()

    assert summary.video_count == 2
    assert summary.collection_run_count == 1
    assert summary.search_hit_count == 1
    assert summary.annotation_count == 1
    assert summary.reviewed_count == 1
    assert summary.unreviewed_count == 1


def test_reader_lists_video_table_rows_with_annotation_fields(
    session_factory: sessionmaker[Session],
) -> None:
    """Video table rows include metadata and compact annotation fields."""

    with session_factory() as session:
        SqlAlchemyVideoRepository(session).add_or_update(
            make_video("video-123", first_seen_at=NOW, title="Sabre final")
        )
        SqlAlchemyAnnotationRepository(session).save(
            ResearchAnnotation(
                youtube_video_id="video-123",
                updated_at=NOW,
                review_status=ReviewStatus.REVIEWED,
                relevance_label="relevant",
            )
        )
        session.commit()

    reader = SqlAlchemyStoredDataReader(session_factory)

    rows = reader.list_video_table_rows(limit=20, offset=0, search=None)

    assert len(rows) == 1
    assert rows[0].youtube_video_id == "video-123"
    assert rows[0].title == "Sabre final"
    assert rows[0].channel_title == "Fencing Channel"
    assert rows[0].duration_seconds == 720
    assert rows[0].view_count == 100
    assert rows[0].review_status == "reviewed"
    assert rows[0].relevance_label == "relevant"
    assert rows[0].video_url == "https://www.youtube.com/watch?v=video-123"


def test_reader_filters_video_table_rows_by_search_text(
    session_factory: sessionmaker[Session],
) -> None:
    """Video table search checks YouTube ID, title, and channel title."""

    with session_factory() as session:
        videos = SqlAlchemyVideoRepository(session)
        videos.add_or_update(make_video("video-1", first_seen_at=NOW, title="Sabre final"))
        videos.add_or_update(make_video("video-2", first_seen_at=NOW, title="Foil lesson"))
        session.commit()

    reader = SqlAlchemyStoredDataReader(session_factory)

    rows = reader.list_video_table_rows(limit=20, offset=0, search="sabre")

    assert [row.youtube_video_id for row in rows] == ["video-1"]


def test_reader_applies_video_table_offset(
    session_factory: sessionmaker[Session],
) -> None:
    """Video table rows support API pagination through offset."""

    with session_factory() as session:
        videos = SqlAlchemyVideoRepository(session)
        videos.add_or_update(
            make_video("video-new", first_seen_at=NOW + timedelta(hours=1), title="New")
        )
        videos.add_or_update(make_video("video-old", first_seen_at=NOW, title="Old"))
        session.commit()

    reader = SqlAlchemyStoredDataReader(session_factory)

    rows = reader.list_video_table_rows(limit=20, offset=1, search=None)

    assert [row.youtube_video_id for row in rows] == ["video-old"]


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


def test_reader_returns_video_detail_with_annotation_and_provenance_summary(
    session_factory: sessionmaker[Session],
) -> None:
    """Video detail includes annotation fields and compact discovery provenance."""

    with session_factory() as session:
        SqlAlchemyVideoRepository(session).add_or_update(
            make_video("video-123", first_seen_at=NOW, title="Sabre final")
        )
        SqlAlchemyAnnotationRepository(session).save(
            ResearchAnnotation(
                youtube_video_id="video-123",
                updated_at=NOW + timedelta(minutes=10),
                review_status=ReviewStatus.REVIEWED,
                notes="Useful reference.",
                relevance_label="relevant",
                competition_name="European Championship",
                fencer_names=("Fencer One", "Fencer Two"),
                weapon_category="sabre",
                event_notes="Final bout",
            )
        )
        collections = SqlAlchemyCollectionRepository(session)
        older_run_id = collections.add_collection_run(
            CollectionRun(
                search_query=SearchQuery("older sabre"),
                started_at=NOW,
            ),
            status="completed",
        )
        newer_run_id = collections.add_collection_run(
            CollectionRun(
                search_query=SearchQuery("newer sabre"),
                started_at=NOW + timedelta(hours=1),
            ),
            status="completed",
        )
        collections.add_search_hit(
            older_run_id,
            youtube_video_id="video-123",
            discovered_at=NOW,
            rank=1,
        )
        collections.add_search_hit(
            newer_run_id,
            youtube_video_id="video-123",
            discovered_at=NOW + timedelta(hours=1),
            rank=1,
        )
        session.commit()

    reader = SqlAlchemyStoredDataReader(session_factory)

    detail = reader.get_video("video-123")

    assert detail is not None
    assert detail.notes == "Useful reference."
    assert detail.relevance_label == "relevant"
    assert detail.competition_name == "European Championship"
    assert detail.fencer_names == ("Fencer One", "Fencer Two")
    assert detail.weapon_category == "sabre"
    assert detail.event_notes == "Final bout"
    assert detail.annotation_updated_at == NOW + timedelta(minutes=10)
    assert detail.discovery_run_count == 2
    assert detail.first_collection_run_started_at == NOW
    assert detail.latest_collection_run_started_at == NOW + timedelta(hours=1)
    assert detail.first_query_text == "older sabre"
    assert detail.latest_query_text == "newer sabre"


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


def test_reader_applies_collection_run_offset(
    session_factory: sessionmaker[Session],
) -> None:
    """Collection-run summaries support API pagination through offset."""

    with session_factory() as session:
        collections = SqlAlchemyCollectionRepository(session)
        collections.add_collection_run(
            CollectionRun(search_query=SearchQuery("older"), started_at=NOW),
            status="completed",
        )
        older_second_id = collections.add_collection_run(
            CollectionRun(search_query=SearchQuery("middle"), started_at=NOW + timedelta(hours=1)),
            status="completed",
        )
        collections.add_collection_run(
            CollectionRun(search_query=SearchQuery("newer"), started_at=NOW + timedelta(hours=2)),
            status="completed",
        )
        session.commit()

    reader = SqlAlchemyStoredDataReader(session_factory)

    summaries = reader.list_collection_runs(limit=1, offset=1)

    assert [summary.run_id for summary in summaries] == [older_second_id]


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


def test_reader_lists_search_hit_table_rows_with_annotation_summary(
    session_factory: sessionmaker[Session],
) -> None:
    """Search-hit table rows include provenance, video, and annotation fields."""

    with session_factory() as session:
        SqlAlchemyVideoRepository(session).add_or_update(
            make_video("video-123", first_seen_at=NOW, title="Sabre final")
        )
        SqlAlchemyAnnotationRepository(session).save(
            ResearchAnnotation(
                youtube_video_id="video-123",
                updated_at=NOW,
                review_status=ReviewStatus.REVIEWED,
                relevance_label="relevant",
            )
        )
        collections = SqlAlchemyCollectionRepository(session)
        run_id = collections.add_collection_run(
            CollectionRun(search_query=SearchQuery("sabre final"), started_at=NOW),
            status="completed",
        )
        collections.add_search_hit(
            run_id,
            youtube_video_id="video-123",
            discovered_at=NOW + timedelta(seconds=30),
            rank=3,
        )
        session.commit()

    reader = SqlAlchemyStoredDataReader(session_factory)

    rows = reader.list_search_hit_table_rows(limit=20, offset=0, query_text=None)

    assert len(rows) == 1
    assert rows[0].collection_run_id == run_id
    assert rows[0].query_text == "sabre final"
    assert rows[0].run_started_at == NOW
    assert rows[0].rank == 3
    assert rows[0].discovered_at == NOW + timedelta(seconds=30)
    assert rows[0].youtube_video_id == "video-123"
    assert rows[0].title == "Sabre final"
    assert rows[0].channel_title == "Fencing Channel"
    assert rows[0].review_status == "reviewed"
    assert rows[0].relevance_label == "relevant"


def test_reader_filters_search_hit_table_rows_by_query_text(
    session_factory: sessionmaker[Session],
) -> None:
    """Search-hit table rows support simple query-text filtering."""

    with session_factory() as session:
        videos = SqlAlchemyVideoRepository(session)
        videos.add_or_update(make_video("sabre-video", first_seen_at=NOW, title="Sabre"))
        videos.add_or_update(make_video("foil-video", first_seen_at=NOW, title="Foil"))
        collections = SqlAlchemyCollectionRepository(session)
        sabre_run_id = collections.add_collection_run(
            CollectionRun(search_query=SearchQuery("sabre final"), started_at=NOW),
            status="completed",
        )
        foil_run_id = collections.add_collection_run(
            CollectionRun(search_query=SearchQuery("foil final"), started_at=NOW),
            status="completed",
        )
        collections.add_search_hit(
            sabre_run_id,
            youtube_video_id="sabre-video",
            discovered_at=NOW,
            rank=1,
        )
        collections.add_search_hit(
            foil_run_id,
            youtube_video_id="foil-video",
            discovered_at=NOW,
            rank=1,
        )
        session.commit()

    reader = SqlAlchemyStoredDataReader(session_factory)

    rows = reader.list_search_hit_table_rows(limit=20, offset=0, query_text="sabre")

    assert [row.youtube_video_id for row in rows] == ["sabre-video"]


def test_reader_applies_search_hit_table_offset(
    session_factory: sessionmaker[Session],
) -> None:
    """Search-hit table rows support API pagination through offset."""

    with session_factory() as session:
        videos = SqlAlchemyVideoRepository(session)
        videos.add_or_update(make_video("new-video", first_seen_at=NOW, title="New"))
        videos.add_or_update(make_video("old-video", first_seen_at=NOW, title="Old"))
        collections = SqlAlchemyCollectionRepository(session)
        old_run_id = collections.add_collection_run(
            CollectionRun(search_query=SearchQuery("older"), started_at=NOW),
            status="completed",
        )
        new_run_id = collections.add_collection_run(
            CollectionRun(search_query=SearchQuery("newer"), started_at=NOW + timedelta(hours=1)),
            status="completed",
        )
        collections.add_search_hit(
            old_run_id,
            youtube_video_id="old-video",
            discovered_at=NOW,
            rank=1,
        )
        collections.add_search_hit(
            new_run_id,
            youtube_video_id="new-video",
            discovered_at=NOW + timedelta(hours=1),
            rank=1,
        )
        session.commit()

    reader = SqlAlchemyStoredDataReader(session_factory)

    rows = reader.list_search_hit_table_rows(limit=20, offset=1, query_text=None)

    assert [row.youtube_video_id for row in rows] == ["old-video"]
