"""Tests for the application-layer video collection use case."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from types import TracebackType
from typing import Self

import pytest

from fencing_video_research_agent.application import (
    CollectVideosRequest,
    CollectVideosUseCase,
    MissingYouTubeMetadataError,
)
from fencing_video_research_agent.domain import (
    CollectionRun,
    ResearchAnnotation,
    SearchQuery,
    Video,
    YouTubeMetadata,
)
from fencing_video_research_agent.ports import (
    CollectionRunRecordId,
    PermanentYouTubeGatewayError,
    SearchQueryRecordId,
    TransientYouTubeGatewayError,
    VideoRecordId,
    YouTubeSearchRequest,
    YouTubeSearchResult,
)

STARTED_AT = datetime(2026, 7, 13, 9, 0, tzinfo=UTC)
COMPLETED_AT = datetime(2026, 7, 13, 9, 1, tzinfo=UTC)
PUBLISHED_AT = datetime(2026, 7, 12, 18, 30, tzinfo=UTC)


def make_metadata(
    youtube_video_id: str,
    *,
    description: str | None = "A sabre fencing bout.",
    published_at: datetime | None = PUBLISHED_AT,
    duration: timedelta | None = timedelta(minutes=9),
    view_count: int | None = 120,
    like_count: int | None = 15,
    comment_count: int | None = 3,
    thumbnail_url: str | None = "https://example.test/thumb.jpg",
    video_url: str | None = "https://example.test/video",
) -> YouTubeMetadata:
    """Create valid project-owned metadata for fake gateway tests."""

    return YouTubeMetadata(
        youtube_video_id=youtube_video_id,
        title=f"Sabre bout {youtube_video_id}",
        description=description,
        channel_id="channel-123",
        channel_title="Fencing Channel",
        published_at=published_at,
        duration=duration,
        view_count=view_count,
        like_count=like_count,
        comment_count=comment_count,
        last_refreshed_at=COMPLETED_AT,
        tags=(),
        thumbnail_url=thumbnail_url,
        video_url=video_url,
    )


class FakeClock:
    """Deterministic clock for application tests."""

    def __init__(self, *values: datetime) -> None:
        self._values = list(values)

    def utcnow(self) -> datetime:
        if self._values:
            return self._values.pop(0)
        return COMPLETED_AT


class FakeYouTubeGateway:
    """Offline fake that returns project-owned YouTube DTOs."""

    def __init__(
        self,
        *,
        search_results: Sequence[YouTubeSearchResult] = (),
        metadata: Sequence[YouTubeMetadata] = (),
        search_error: Exception | None = None,
        metadata_error: Exception | None = None,
    ) -> None:
        self._search_results = tuple(search_results)
        self._metadata = tuple(metadata)
        self._search_error = search_error
        self._metadata_error = metadata_error
        self.search_requests: list[YouTubeSearchRequest] = []
        self.metadata_requests: list[tuple[str, ...]] = []

    def search_videos(self, request: YouTubeSearchRequest) -> tuple[YouTubeSearchResult, ...]:
        self.search_requests.append(request)
        if self._search_error is not None:
            raise self._search_error
        return self._search_results

    def fetch_video_metadata(self, video_ids: Sequence[str]) -> tuple[YouTubeMetadata, ...]:
        self.metadata_requests.append(tuple(video_ids))
        if self._metadata_error is not None:
            raise self._metadata_error
        return self._metadata


@dataclass
class FakeVideoRepository:
    """Fake video repository that records saved domain videos."""

    videos_by_id: dict[str, Video] = field(default_factory=dict)
    saved_videos: list[Video] = field(default_factory=list)

    def get_by_youtube_id(self, youtube_video_id: str) -> Video | None:
        return self.videos_by_id.get(youtube_video_id)

    def add_or_update(self, video: Video) -> VideoRecordId:
        self.videos_by_id[video.youtube_video_id] = video
        self.saved_videos.append(video)
        return VideoRecordId(len(self.videos_by_id))


@dataclass
class RecordedSearchHit:
    """A search hit captured by the fake collection repository."""

    collection_run_id: CollectionRunRecordId
    youtube_video_id: str
    discovered_at: datetime
    rank: int | None


@dataclass
class FakeCollectionRepository:
    """Fake collection repository for query, run, and hit assertions."""

    fail_on_search_hit: bool = False
    search_queries: list[SearchQuery] = field(default_factory=list)
    collection_runs: list[CollectionRun] = field(default_factory=list)
    collection_run_statuses: list[str] = field(default_factory=list)
    search_hits: list[RecordedSearchHit] = field(default_factory=list)

    def get_or_create_search_query(
        self,
        query: SearchQuery,
        *,
        created_at: datetime,
    ) -> SearchQueryRecordId:
        self.search_queries.append(query)
        return SearchQueryRecordId(len(self.search_queries))

    def add_collection_run(
        self,
        run: CollectionRun,
        *,
        status: str,
        error_message: str | None = None,
    ) -> CollectionRunRecordId:
        self.collection_runs.append(run)
        self.collection_run_statuses.append(status)
        return CollectionRunRecordId(len(self.collection_runs))

    def add_search_hit(
        self,
        collection_run_id: CollectionRunRecordId,
        *,
        youtube_video_id: str,
        discovered_at: datetime,
        rank: int | None = None,
    ) -> None:
        if self.fail_on_search_hit:
            raise RuntimeError("persistence failed")
        self.search_hits.append(
            RecordedSearchHit(
                collection_run_id=collection_run_id,
                youtube_video_id=youtube_video_id,
                discovered_at=discovered_at,
                rank=rank,
            )
        )


class FakeAnnotationRepository:
    """Fake annotation repository required by the Unit of Work port."""

    def get_by_youtube_id(self, youtube_video_id: str) -> ResearchAnnotation | None:
        return None

    def save(self, annotation: ResearchAnnotation) -> None:
        return None


class FakeUnitOfWork:
    """Fake Unit of Work with explicit commit and rollback tracking."""

    def __init__(self, collections: FakeCollectionRepository | None = None) -> None:
        self.videos = FakeVideoRepository()
        self.collections = collections or FakeCollectionRepository()
        self.annotations = FakeAnnotationRepository()
        self.entered = False
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def __enter__(self) -> Self:
        self.entered = True
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc_type is not None or not self.committed:
            self.rollback()
        self.closed = True

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True


class FakeUnitOfWorkFactory:
    """Callable factory that records how often persistence is opened."""

    def __init__(self, unit_of_work: FakeUnitOfWork) -> None:
        self.unit_of_work = unit_of_work
        self.calls = 0

    def __call__(self) -> FakeUnitOfWork:
        self.calls += 1
        return self.unit_of_work


def make_use_case(
    *,
    gateway: FakeYouTubeGateway,
    unit_of_work: FakeUnitOfWork | None = None,
) -> tuple[CollectVideosUseCase, FakeUnitOfWorkFactory]:
    """Build the use case with deterministic fakes."""

    fake_unit_of_work = unit_of_work or FakeUnitOfWork()
    unit_of_work_factory = FakeUnitOfWorkFactory(fake_unit_of_work)
    return (
        CollectVideosUseCase(
            youtube_gateway=gateway,
            unit_of_work_factory=unit_of_work_factory,
            clock=FakeClock(STARTED_AT, COMPLETED_AT),
        ),
        unit_of_work_factory,
    )


def test_successful_collection_stores_videos_query_run_and_hits() -> None:
    gateway = FakeYouTubeGateway(
        search_results=(
            YouTubeSearchResult(youtube_video_id="video-1", rank=1),
            YouTubeSearchResult(youtube_video_id="video-2", rank=2),
        ),
        metadata=(make_metadata("video-1"), make_metadata("video-2")),
    )
    use_case, unit_of_work_factory = make_use_case(gateway=gateway)

    result = use_case.execute(
        CollectVideosRequest(
            query_text=" sabre fencing ",
            max_results=2,
            parameters={"order": "date"},
        )
    )

    unit_of_work = unit_of_work_factory.unit_of_work
    assert result.collection_run_id == CollectionRunRecordId(1)
    assert result.search_result_count == 2
    assert result.unique_video_count == 2
    assert result.stored_video_count == 2
    assert result.search_hit_count == 2
    assert result.duplicate_search_result_count == 0
    assert gateway.metadata_requests == [("video-1", "video-2")]
    assert [video.youtube_video_id for video in unit_of_work.videos.saved_videos] == [
        "video-1",
        "video-2",
    ]
    assert len(unit_of_work.collections.collection_runs) == 1
    assert unit_of_work.collections.collection_run_statuses == ["completed"]
    assert [(hit.youtube_video_id, hit.rank) for hit in unit_of_work.collections.search_hits] == [
        ("video-1", 1),
        ("video-2", 2),
    ]
    assert unit_of_work.committed is True
    assert unit_of_work.rolled_back is False
    assert unit_of_work.closed is True


def test_duplicate_search_results_are_deduplicated_before_metadata_fetch() -> None:
    gateway = FakeYouTubeGateway(
        search_results=(
            YouTubeSearchResult(youtube_video_id="video-2", rank=2),
            YouTubeSearchResult(youtube_video_id="video-1", rank=1),
            YouTubeSearchResult(youtube_video_id="video-2", rank=3),
        ),
        metadata=(make_metadata("video-2"), make_metadata("video-1")),
    )
    use_case, unit_of_work_factory = make_use_case(gateway=gateway)

    result = use_case.execute(
        CollectVideosRequest(query_text="sabre fencing", max_results=3),
    )

    unit_of_work = unit_of_work_factory.unit_of_work
    assert gateway.metadata_requests == [("video-2", "video-1")]
    assert result.duplicate_search_result_count == 1
    assert [(hit.youtube_video_id, hit.rank) for hit in unit_of_work.collections.search_hits] == [
        ("video-2", 2),
        ("video-1", 1),
    ]


def test_empty_search_results_record_completed_run_without_metadata_fetch() -> None:
    gateway = FakeYouTubeGateway(search_results=(), metadata=())
    use_case, unit_of_work_factory = make_use_case(gateway=gateway)

    result = use_case.execute(
        CollectVideosRequest(query_text="sabre fencing", max_results=5),
    )

    unit_of_work = unit_of_work_factory.unit_of_work
    assert gateway.metadata_requests == []
    assert result.search_result_count == 0
    assert result.unique_video_count == 0
    assert result.search_hit_count == 0
    assert unit_of_work.collections.collection_run_statuses == ["completed"]
    assert unit_of_work.collections.search_hits == []
    assert unit_of_work.committed is True


def test_missing_metadata_raises_and_does_not_commit() -> None:
    gateway = FakeYouTubeGateway(
        search_results=(
            YouTubeSearchResult(youtube_video_id="video-1", rank=1),
            YouTubeSearchResult(youtube_video_id="video-2", rank=2),
        ),
        metadata=(make_metadata("video-1"),),
    )
    use_case, unit_of_work_factory = make_use_case(gateway=gateway)

    with pytest.raises(MissingYouTubeMetadataError) as error:
        use_case.execute(CollectVideosRequest(query_text="sabre fencing", max_results=2))

    assert error.value.missing_video_ids == ("video-2",)
    assert unit_of_work_factory.calls == 0
    assert unit_of_work_factory.unit_of_work.committed is False


def test_optional_missing_metadata_fields_are_accepted_as_none() -> None:
    metadata = make_metadata(
        "video-1",
        description=None,
        published_at=None,
        duration=None,
        view_count=None,
        like_count=None,
        comment_count=None,
        thumbnail_url=None,
        video_url=None,
    )
    gateway = FakeYouTubeGateway(
        search_results=(YouTubeSearchResult(youtube_video_id="video-1", rank=1),),
        metadata=(metadata,),
    )
    use_case, unit_of_work_factory = make_use_case(gateway=gateway)

    use_case.execute(CollectVideosRequest(query_text="sabre fencing", max_results=1))

    stored_metadata = unit_of_work_factory.unit_of_work.videos.saved_videos[0].metadata
    assert stored_metadata.description is None
    assert stored_metadata.published_at is None
    assert stored_metadata.duration is None
    assert stored_metadata.view_count is None
    assert stored_metadata.thumbnail_url is None


def test_transient_gateway_error_propagates_without_opening_unit_of_work() -> None:
    gateway = FakeYouTubeGateway(search_error=TransientYouTubeGatewayError("temporary outage"))
    use_case, unit_of_work_factory = make_use_case(gateway=gateway)

    with pytest.raises(TransientYouTubeGatewayError, match="temporary outage"):
        use_case.execute(CollectVideosRequest(query_text="sabre fencing", max_results=1))

    assert unit_of_work_factory.calls == 0


def test_permanent_gateway_error_propagates_without_opening_unit_of_work() -> None:
    gateway = FakeYouTubeGateway(search_error=PermanentYouTubeGatewayError("invalid parameter"))
    use_case, unit_of_work_factory = make_use_case(gateway=gateway)

    with pytest.raises(PermanentYouTubeGatewayError, match="invalid parameter"):
        use_case.execute(CollectVideosRequest(query_text="sabre fencing", max_results=1))

    assert unit_of_work_factory.calls == 0


def test_persistence_failure_triggers_rollback_without_commit() -> None:
    gateway = FakeYouTubeGateway(
        search_results=(YouTubeSearchResult(youtube_video_id="video-1", rank=1),),
        metadata=(make_metadata("video-1"),),
    )
    unit_of_work = FakeUnitOfWork(
        collections=FakeCollectionRepository(fail_on_search_hit=True),
    )
    use_case, unit_of_work_factory = make_use_case(
        gateway=gateway,
        unit_of_work=unit_of_work,
    )

    with pytest.raises(RuntimeError, match="persistence failed"):
        use_case.execute(CollectVideosRequest(query_text="sabre fencing", max_results=1))

    assert unit_of_work_factory.calls == 1
    assert unit_of_work.committed is False
    assert unit_of_work.rolled_back is True
    assert unit_of_work.closed is True


def test_max_results_and_request_parameters_are_recorded_in_search_query() -> None:
    gateway = FakeYouTubeGateway(search_results=(), metadata=())
    use_case, unit_of_work_factory = make_use_case(gateway=gateway)

    use_case.execute(
        CollectVideosRequest(
            query_text="sabre fencing",
            max_results=25,
            parameters={"order": "relevance", "videoEmbeddable": True},
        )
    )

    stored_query = unit_of_work_factory.unit_of_work.collections.collection_runs[0].search_query
    assert dict(stored_query.parameters) == {
        "max_results": 25,
        "order": "relevance",
        "videoEmbeddable": True,
    }


def test_request_copies_parameters_and_rejects_invalid_values() -> None:
    parameters = {"order": "date"}

    request = CollectVideosRequest(
        query_text=" sabre fencing ",
        max_results=5,
        parameters=parameters,
    )
    parameters["order"] = "relevance"

    assert request.query_text == "sabre fencing"
    assert request.parameters["order"] == "date"
    with pytest.raises(ValueError, match="query_text"):
        CollectVideosRequest(query_text=" ", max_results=5)
    with pytest.raises(ValueError, match="max_results"):
        CollectVideosRequest(query_text="sabre fencing", max_results=0)


def test_collection_use_case_uses_fake_gateway_without_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    gateway = FakeYouTubeGateway(search_results=(), metadata=())
    use_case, unit_of_work_factory = make_use_case(gateway=gateway)

    use_case.execute(CollectVideosRequest(query_text="sabre fencing", max_results=1))

    assert gateway.search_requests
    assert unit_of_work_factory.unit_of_work.committed is True
