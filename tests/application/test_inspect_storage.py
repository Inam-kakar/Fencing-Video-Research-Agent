"""Tests for read-only stored-video inspection use cases."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import pytest

from fencing_video_research_agent.application import (
    ListCollectionRunsRequest,
    ListCollectionRunsUseCase,
    ListStoredVideosRequest,
    ListStoredVideosUseCase,
    ShowCollectionRunRequest,
    ShowCollectionRunUseCase,
    ShowStoredVideoRequest,
    ShowStoredVideoUseCase,
    StoredCollectionRunNotFoundError,
    StoredVideoNotFoundError,
)
from fencing_video_research_agent.application.inspect_storage import (
    GetStoredDataSummaryRequest,
    GetStoredDataSummaryUseCase,
    ListSearchHitTableRowsRequest,
    ListSearchHitTableRowsUseCase,
    ListVideoTableRowsRequest,
    ListVideoTableRowsUseCase,
)
from fencing_video_research_agent.ports import (
    CollectionRunRecordId,
    StoredCollectionRunDetail,
    StoredCollectionRunHit,
    StoredCollectionRunSummary,
    StoredVideoSummary,
)
from fencing_video_research_agent.ports.stored_data import (
    StoredDataSummary,
    StoredSearchHitTableRow,
    StoredVideoDetail,
    StoredVideoTableRow,
)

NOW = datetime(2026, 7, 13, 8, 0, tzinfo=UTC)


def make_summary(youtube_video_id: str = "video-123") -> StoredVideoSummary:
    """Create a stored-video summary for use-case tests."""

    return StoredVideoSummary(
        youtube_video_id=youtube_video_id,
        title="Sabre final",
        channel_title="Fencing Channel",
        published_at=NOW,
        first_seen_at=NOW,
        last_refreshed_at=NOW,
    )


def make_detail(youtube_video_id: str = "video-123") -> StoredVideoDetail:
    """Create stored-video detail for use-case tests."""

    return StoredVideoDetail(
        youtube_video_id=youtube_video_id,
        title="Sabre final",
        description="A public fencing bout.",
        channel_id="channel-123",
        channel_title="Fencing Channel",
        published_at=NOW,
        duration_seconds=600,
        view_count=100,
        like_count=10,
        comment_count=2,
        tags=("sabre", "final"),
        thumbnail_url="https://example.test/thumb.jpg",
        video_url="https://www.youtube.com/watch?v=video-123",
        first_seen_at=NOW,
        last_refreshed_at=NOW,
        annotation_status="reviewed",
    )


def make_table_row(youtube_video_id: str = "video-123") -> StoredVideoTableRow:
    """Create a stored-video table row for use-case tests."""

    return StoredVideoTableRow(
        youtube_video_id=youtube_video_id,
        title="Sabre final",
        channel_title="Fencing Channel",
        duration_seconds=600,
        published_at=NOW,
        view_count=100,
        review_status="reviewed",
        relevance_label="relevant",
        video_url="https://www.youtube.com/watch?v=video-123",
        first_seen_at=NOW,
        last_refreshed_at=NOW,
    )


def make_run_summary(run_id: int = 1) -> StoredCollectionRunSummary:
    """Create a collection-run summary for use-case tests."""

    return StoredCollectionRunSummary(
        run_id=CollectionRunRecordId(run_id),
        query_text="sabre fencing",
        status="completed",
        started_at=NOW,
        completed_at=NOW,
        hit_count=2,
    )


def make_run_detail(run_id: int = 1) -> StoredCollectionRunDetail:
    """Create collection-run detail for use-case tests."""

    return StoredCollectionRunDetail(
        run_id=CollectionRunRecordId(run_id),
        query_text="sabre fencing",
        query_parameters={"max_results": 2, "order": "date"},
        status="completed",
        started_at=NOW,
        completed_at=NOW,
        hit_count=1,
        hits=(
            StoredCollectionRunHit(
                rank=1,
                youtube_video_id="video-123",
                title="Sabre final",
                channel_title="Fencing Channel",
            ),
        ),
    )


def make_search_hit_row() -> StoredSearchHitTableRow:
    """Create a search-hit table row for use-case tests."""

    return StoredSearchHitTableRow(
        collection_run_id=CollectionRunRecordId(1),
        query_text="sabre fencing",
        run_started_at=NOW,
        rank=1,
        discovered_at=NOW,
        youtube_video_id="video-123",
        title="Sabre final",
        channel_title="Fencing Channel",
        review_status="reviewed",
        relevance_label="relevant",
    )


@dataclass
class FakeStoredDataReader:
    """Read-only fake for application tests."""

    summaries: tuple[StoredVideoSummary, ...] = ()
    summary: StoredDataSummary | None = None
    details_by_id: dict[str, StoredVideoDetail] | None = None
    table_rows: tuple[StoredVideoTableRow, ...] = ()
    search_hit_rows: tuple[StoredSearchHitTableRow, ...] = ()
    run_summaries: tuple[StoredCollectionRunSummary, ...] = ()
    run_details_by_id: dict[int, StoredCollectionRunDetail] | None = None
    list_limits: list[int] | None = None
    table_requests: list[tuple[int, int, str | None]] | None = None
    requested_ids: list[str] | None = None
    run_list_limits: list[int] | None = None
    run_list_offsets: list[int] | None = None
    search_hit_requests: list[tuple[int, int, str | None]] | None = None
    requested_run_ids: list[int] | None = None

    def get_summary(self) -> StoredDataSummary:
        return self.summary or StoredDataSummary(
            video_count=0,
            collection_run_count=0,
            search_hit_count=0,
            annotation_count=0,
            reviewed_count=0,
            unreviewed_count=0,
        )

    def list_videos(self, *, limit: int) -> tuple[StoredVideoSummary, ...]:
        if self.list_limits is not None:
            self.list_limits.append(limit)
        return self.summaries

    def list_video_table_rows(
        self,
        *,
        limit: int,
        offset: int,
        search: str | None,
    ) -> tuple[StoredVideoTableRow, ...]:
        if self.table_requests is not None:
            self.table_requests.append((limit, offset, search))
        return self.table_rows

    def get_video(self, youtube_video_id: str) -> StoredVideoDetail | None:
        if self.requested_ids is not None:
            self.requested_ids.append(youtube_video_id)
        return (self.details_by_id or {}).get(youtube_video_id)

    def list_collection_runs(
        self,
        *,
        limit: int,
        offset: int = 0,
    ) -> tuple[StoredCollectionRunSummary, ...]:
        if self.run_list_limits is not None:
            self.run_list_limits.append(limit)
        if self.run_list_offsets is not None:
            self.run_list_offsets.append(offset)
        return self.run_summaries

    def get_collection_run(
        self,
        run_id: CollectionRunRecordId,
    ) -> StoredCollectionRunDetail | None:
        if self.requested_run_ids is not None:
            self.requested_run_ids.append(int(run_id))
        return (self.run_details_by_id or {}).get(int(run_id))

    def list_search_hit_table_rows(
        self,
        *,
        limit: int,
        offset: int,
        query_text: str | None,
    ) -> tuple[StoredSearchHitTableRow, ...]:
        if self.search_hit_requests is not None:
            self.search_hit_requests.append((limit, offset, query_text))
        return self.search_hit_rows


def test_get_stored_data_summary_returns_reader_counts() -> None:
    summary = StoredDataSummary(
        video_count=3,
        collection_run_count=2,
        search_hit_count=4,
        annotation_count=1,
        reviewed_count=1,
        unreviewed_count=2,
    )
    reader = FakeStoredDataReader(summary=summary)
    use_case = GetStoredDataSummaryUseCase(stored_data_reader=reader)

    result = use_case.execute(GetStoredDataSummaryRequest())

    assert result.summary == summary


def test_list_stored_videos_returns_reader_summaries() -> None:
    limits: list[int] = []
    reader = FakeStoredDataReader(summaries=(make_summary(),), list_limits=limits)
    use_case = ListStoredVideosUseCase(stored_data_reader=reader)

    result = use_case.execute(ListStoredVideosRequest(limit=5))

    assert limits == [5]
    assert [video.youtube_video_id for video in result.videos] == ["video-123"]


def test_list_stored_videos_accepts_empty_result() -> None:
    reader = FakeStoredDataReader()
    use_case = ListStoredVideosUseCase(stored_data_reader=reader)

    result = use_case.execute(ListStoredVideosRequest(limit=20))

    assert result.videos == ()


def test_list_stored_videos_rejects_invalid_limits() -> None:
    with pytest.raises(ValueError, match="positive"):
        ListStoredVideosRequest(limit=0)
    with pytest.raises(ValueError, match="at most"):
        ListStoredVideosRequest(limit=101)


def test_list_video_table_rows_passes_pagination_and_trimmed_search() -> None:
    requests: list[tuple[int, int, str | None]] = []
    reader = FakeStoredDataReader(
        table_rows=(make_table_row(),),
        table_requests=requests,
    )
    use_case = ListVideoTableRowsUseCase(stored_data_reader=reader)

    result = use_case.execute(ListVideoTableRowsRequest(limit=10, offset=5, search=" sabre "))

    assert requests == [(10, 5, "sabre")]
    assert [video.youtube_video_id for video in result.videos] == ["video-123"]


def test_list_video_table_rows_normalizes_blank_search_to_none() -> None:
    requests: list[tuple[int, int, str | None]] = []
    reader = FakeStoredDataReader(table_requests=requests)
    use_case = ListVideoTableRowsUseCase(stored_data_reader=reader)

    use_case.execute(ListVideoTableRowsRequest(limit=10, offset=0, search="  "))

    assert requests == [(10, 0, None)]


def test_list_video_table_rows_rejects_invalid_pagination() -> None:
    with pytest.raises(ValueError, match="positive"):
        ListVideoTableRowsRequest(limit=0)
    with pytest.raises(ValueError, match="at most"):
        ListVideoTableRowsRequest(limit=101)
    with pytest.raises(ValueError, match="offset"):
        ListVideoTableRowsRequest(offset=-1)


def test_show_stored_video_returns_reader_detail() -> None:
    requested_ids: list[str] = []
    reader = FakeStoredDataReader(
        details_by_id={"video-123": make_detail()},
        requested_ids=requested_ids,
    )
    use_case = ShowStoredVideoUseCase(stored_data_reader=reader)

    result = use_case.execute(ShowStoredVideoRequest(youtube_video_id=" video-123 "))

    assert requested_ids == ["video-123"]
    assert result.video.title == "Sabre final"


def test_show_stored_video_raises_for_missing_video() -> None:
    reader = FakeStoredDataReader(details_by_id={})
    use_case = ShowStoredVideoUseCase(stored_data_reader=reader)

    with pytest.raises(StoredVideoNotFoundError) as error:
        use_case.execute(ShowStoredVideoRequest(youtube_video_id="missing-video"))

    assert error.value.youtube_video_id == "missing-video"


def test_list_collection_runs_returns_reader_summaries() -> None:
    limits: list[int] = []
    offsets: list[int] = []
    reader = FakeStoredDataReader(
        run_summaries=(make_run_summary(),),
        run_list_limits=limits,
        run_list_offsets=offsets,
    )
    use_case = ListCollectionRunsUseCase(stored_data_reader=reader)

    result = use_case.execute(ListCollectionRunsRequest(limit=5, offset=2))

    assert limits == [5]
    assert offsets == [2]
    assert [int(run.run_id) for run in result.runs] == [1]


def test_list_collection_runs_accepts_empty_result() -> None:
    reader = FakeStoredDataReader()
    use_case = ListCollectionRunsUseCase(stored_data_reader=reader)

    result = use_case.execute(ListCollectionRunsRequest(limit=20))

    assert result.runs == ()


def test_list_collection_runs_rejects_invalid_limits() -> None:
    with pytest.raises(ValueError, match="positive"):
        ListCollectionRunsRequest(limit=0)
    with pytest.raises(ValueError, match="at most"):
        ListCollectionRunsRequest(limit=101)
    with pytest.raises(ValueError, match="offset"):
        ListCollectionRunsRequest(offset=-1)


def test_show_collection_run_returns_reader_detail() -> None:
    requested_run_ids: list[int] = []
    reader = FakeStoredDataReader(
        run_details_by_id={1: make_run_detail()},
        requested_run_ids=requested_run_ids,
    )
    use_case = ShowCollectionRunUseCase(stored_data_reader=reader)

    result = use_case.execute(ShowCollectionRunRequest(run_id=1))

    assert requested_run_ids == [1]
    assert result.run.query_text == "sabre fencing"


def test_show_collection_run_raises_for_missing_run() -> None:
    reader = FakeStoredDataReader(run_details_by_id={})
    use_case = ShowCollectionRunUseCase(stored_data_reader=reader)

    with pytest.raises(StoredCollectionRunNotFoundError) as error:
        use_case.execute(ShowCollectionRunRequest(run_id=999))

    assert error.value.run_id == 999


def test_show_collection_run_rejects_invalid_run_id() -> None:
    with pytest.raises(ValueError, match="run_id"):
        ShowCollectionRunRequest(run_id=0)


def test_list_search_hit_table_rows_passes_pagination_and_trimmed_query_text() -> None:
    requests: list[tuple[int, int, str | None]] = []
    reader = FakeStoredDataReader(
        search_hit_rows=(make_search_hit_row(),),
        search_hit_requests=requests,
    )
    use_case = ListSearchHitTableRowsUseCase(stored_data_reader=reader)

    result = use_case.execute(
        ListSearchHitTableRowsRequest(limit=10, offset=3, query_text=" sabre ")
    )

    assert requests == [(10, 3, "sabre")]
    assert [hit.youtube_video_id for hit in result.search_hits] == ["video-123"]


def test_list_search_hit_table_rows_normalizes_blank_query_text_to_none() -> None:
    requests: list[tuple[int, int, str | None]] = []
    reader = FakeStoredDataReader(search_hit_requests=requests)
    use_case = ListSearchHitTableRowsUseCase(stored_data_reader=reader)

    use_case.execute(ListSearchHitTableRowsRequest(limit=10, offset=0, query_text="  "))

    assert requests == [(10, 0, None)]


def test_list_search_hit_table_rows_rejects_invalid_pagination() -> None:
    with pytest.raises(ValueError, match="positive"):
        ListSearchHitTableRowsRequest(limit=0)
    with pytest.raises(ValueError, match="at most"):
        ListSearchHitTableRowsRequest(limit=101)
    with pytest.raises(ValueError, match="offset"):
        ListSearchHitTableRowsRequest(offset=-1)
