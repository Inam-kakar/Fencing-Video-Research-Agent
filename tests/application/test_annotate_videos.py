"""Tests for manual annotation application use cases."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from types import TracebackType
from typing import Self

import pytest

from fencing_video_research_agent.application import (
    AnnotationVideoNotFoundError,
    ClearAnnotationLabelRequest,
    ClearAnnotationLabelUseCase,
    InvalidReviewStatusError,
    SetAnnotationLabelRequest,
    SetAnnotationLabelUseCase,
    SetAnnotationNotesRequest,
    SetAnnotationNotesUseCase,
    SetAnnotationReviewStatusRequest,
    SetAnnotationReviewStatusUseCase,
    ShowAnnotationRequest,
    ShowAnnotationUseCase,
    UpdateAnnotationRequest,
    UpdateAnnotationUseCase,
)
from fencing_video_research_agent.domain import (
    ResearchAnnotation,
    ReviewStatus,
    Video,
    YouTubeMetadata,
)
from fencing_video_research_agent.ports import RepositoryError

NOW = datetime(2026, 7, 14, 9, 0, tzinfo=UTC)


class FixedClock:
    """Clock fake that returns one deterministic UTC timestamp."""

    def __init__(self, now: datetime = NOW) -> None:
        self.now = now

    def utcnow(self) -> datetime:
        return self.now


@dataclass
class FakeVideoRepository:
    """In-memory video repository fake."""

    videos: dict[str, Video] = field(default_factory=dict)

    def get_by_youtube_id(self, youtube_video_id: str) -> Video | None:
        return self.videos.get(youtube_video_id)


@dataclass
class FakeAnnotationRepository:
    """In-memory annotation repository fake."""

    annotations: dict[str, ResearchAnnotation] = field(default_factory=dict)
    saved: list[ResearchAnnotation] = field(default_factory=list)
    fail_on_save: bool = False

    def get_by_youtube_id(self, youtube_video_id: str) -> ResearchAnnotation | None:
        return self.annotations.get(youtube_video_id)

    def save(self, annotation: ResearchAnnotation) -> None:
        if self.fail_on_save:
            msg = "annotation save failed"
            raise RepositoryError(msg)
        self.saved.append(annotation)
        self.annotations[annotation.youtube_video_id] = annotation


@dataclass
class FakeUnitOfWork:
    """Unit of Work fake that records transaction behavior."""

    videos: FakeVideoRepository
    annotations: FakeAnnotationRepository
    commit_count: int = 0
    rollback_count: int = 0

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exc, traceback
        if exc_type is not None or self.commit_count == 0:
            self.rollback()

    def commit(self) -> None:
        self.commit_count += 1

    def rollback(self) -> None:
        self.rollback_count += 1


def make_video(youtube_video_id: str = "video-123") -> Video:
    """Create a valid stored video for annotation tests."""

    metadata = YouTubeMetadata(
        youtube_video_id=youtube_video_id,
        title="Sabre final",
        description="A public fencing bout.",
        channel_id="channel-123",
        channel_title="Fencing Channel",
        published_at=NOW - timedelta(days=1),
        duration=timedelta(minutes=10),
        view_count=100,
        like_count=10,
        comment_count=2,
        last_refreshed_at=NOW,
        tags=("sabre",),
        video_url=f"https://www.youtube.com/watch?v={youtube_video_id}",
    )
    return Video(
        youtube_video_id=youtube_video_id,
        first_seen_at=NOW,
        metadata=metadata,
    )


def make_annotation(
    *,
    youtube_video_id: str = "video-123",
    review_status: ReviewStatus = ReviewStatus.UNREVIEWED,
    notes: str | None = "Needs review.",
    relevance_label: str | None = "candidate",
) -> ResearchAnnotation:
    """Create a valid research annotation for tests."""

    return ResearchAnnotation(
        youtube_video_id=youtube_video_id,
        updated_at=NOW,
        review_status=review_status,
        notes=notes,
        relevance_label=relevance_label,
        competition_name="European Championship",
        fencer_names=("Fencer One",),
        weapon_category="sabre",
        event_notes="Final bout",
    )


def make_unit_of_work(
    *,
    video: Video | None = None,
    annotation: ResearchAnnotation | None = None,
    fail_on_save: bool = False,
) -> FakeUnitOfWork:
    """Create a fake Unit of Work for one stored-video annotation workflow."""

    videos = {}
    if video is not None:
        videos[video.youtube_video_id] = video
    annotations = {}
    if annotation is not None:
        annotations[annotation.youtube_video_id] = annotation
    return FakeUnitOfWork(
        videos=FakeVideoRepository(videos=videos),
        annotations=FakeAnnotationRepository(
            annotations=annotations,
            fail_on_save=fail_on_save,
        ),
    )


def test_show_annotation_raises_for_missing_video() -> None:
    unit_of_work = make_unit_of_work()
    use_case = ShowAnnotationUseCase(unit_of_work_factory=lambda: unit_of_work)

    with pytest.raises(AnnotationVideoNotFoundError) as error:
        use_case.execute(ShowAnnotationRequest(youtube_video_id="missing-video"))

    assert error.value.youtube_video_id == "missing-video"
    assert unit_of_work.commit_count == 0


def test_show_annotation_returns_none_when_video_has_no_annotation() -> None:
    unit_of_work = make_unit_of_work(video=make_video())
    use_case = ShowAnnotationUseCase(unit_of_work_factory=lambda: unit_of_work)

    result = use_case.execute(ShowAnnotationRequest(youtube_video_id="video-123"))

    assert result.youtube_video_id == "video-123"
    assert result.annotation is None
    assert unit_of_work.commit_count == 0


def test_show_annotation_returns_existing_annotation() -> None:
    annotation = make_annotation(review_status=ReviewStatus.REVIEWED)
    unit_of_work = make_unit_of_work(video=make_video(), annotation=annotation)
    use_case = ShowAnnotationUseCase(unit_of_work_factory=lambda: unit_of_work)

    result = use_case.execute(ShowAnnotationRequest(youtube_video_id="video-123"))

    assert result.annotation == annotation


def test_set_status_creates_annotation_if_missing() -> None:
    unit_of_work = make_unit_of_work(video=make_video())
    use_case = SetAnnotationReviewStatusUseCase(
        unit_of_work_factory=lambda: unit_of_work,
        clock=FixedClock(),
    )

    result = use_case.execute(
        SetAnnotationReviewStatusRequest(
            youtube_video_id="video-123",
            status="reviewed",
        )
    )

    assert result.annotation.review_status is ReviewStatus.REVIEWED
    assert result.annotation.youtube_video_id == "video-123"
    assert unit_of_work.annotations.get_by_youtube_id("video-123") == result.annotation
    assert unit_of_work.commit_count == 1


def test_set_status_updates_existing_annotation_and_preserves_other_fields() -> None:
    existing = make_annotation(
        review_status=ReviewStatus.UNREVIEWED,
        notes="Important bout.",
        relevance_label="high-value",
    )
    unit_of_work = make_unit_of_work(video=make_video(), annotation=existing)
    use_case = SetAnnotationReviewStatusUseCase(
        unit_of_work_factory=lambda: unit_of_work,
        clock=FixedClock(),
    )

    result = use_case.execute(
        SetAnnotationReviewStatusRequest(
            youtube_video_id="video-123",
            status="reviewed",
        )
    )

    assert result.annotation.review_status is ReviewStatus.REVIEWED
    assert result.annotation.notes == "Important bout."
    assert result.annotation.relevance_label == "high-value"
    assert result.annotation.competition_name == existing.competition_name
    assert result.annotation.fencer_names == existing.fencer_names
    assert unit_of_work.commit_count == 1


def test_set_status_rejects_invalid_review_status() -> None:
    unit_of_work = make_unit_of_work(video=make_video())
    use_case = SetAnnotationReviewStatusUseCase(
        unit_of_work_factory=lambda: unit_of_work,
        clock=FixedClock(),
    )

    with pytest.raises(InvalidReviewStatusError):
        use_case.execute(
            SetAnnotationReviewStatusRequest(
                youtube_video_id="video-123",
                status="relevant",
            )
        )

    assert unit_of_work.commit_count == 0


def test_set_notes_creates_annotation_if_missing() -> None:
    unit_of_work = make_unit_of_work(video=make_video())
    use_case = SetAnnotationNotesUseCase(
        unit_of_work_factory=lambda: unit_of_work,
        clock=FixedClock(),
    )

    result = use_case.execute(
        SetAnnotationNotesRequest(
            youtube_video_id="video-123",
            notes="Watch for sabre footwork.",
        )
    )

    assert result.annotation.notes == "Watch for sabre footwork."
    assert result.annotation.review_status is ReviewStatus.UNREVIEWED
    assert unit_of_work.commit_count == 1


def test_set_notes_updates_existing_notes() -> None:
    existing = make_annotation(notes="Old notes.", relevance_label="candidate")
    unit_of_work = make_unit_of_work(video=make_video(), annotation=existing)
    use_case = SetAnnotationNotesUseCase(
        unit_of_work_factory=lambda: unit_of_work,
        clock=FixedClock(),
    )

    result = use_case.execute(
        SetAnnotationNotesRequest(
            youtube_video_id="video-123",
            notes="Updated notes.",
        )
    )

    assert result.annotation.notes == "Updated notes."
    assert result.annotation.relevance_label == "candidate"
    assert unit_of_work.commit_count == 1


def test_set_label_creates_annotation_if_missing() -> None:
    unit_of_work = make_unit_of_work(video=make_video())
    use_case = SetAnnotationLabelUseCase(
        unit_of_work_factory=lambda: unit_of_work,
        clock=FixedClock(),
    )

    result = use_case.execute(
        SetAnnotationLabelRequest(youtube_video_id="video-123", label="relevant")
    )

    assert result.annotation.relevance_label == "relevant"
    assert result.annotation.review_status is ReviewStatus.UNREVIEWED
    assert unit_of_work.commit_count == 1


def test_set_label_updates_single_label_and_preserves_unrelated_fields() -> None:
    existing = make_annotation(
        review_status=ReviewStatus.REVIEWED,
        notes="Keep these notes.",
        relevance_label="candidate",
    )
    unit_of_work = make_unit_of_work(video=make_video(), annotation=existing)
    use_case = SetAnnotationLabelUseCase(
        unit_of_work_factory=lambda: unit_of_work,
        clock=FixedClock(),
    )

    result = use_case.execute(
        SetAnnotationLabelRequest(youtube_video_id="video-123", label="gold-medal")
    )

    assert result.annotation.relevance_label == "gold-medal"
    assert result.annotation.review_status is ReviewStatus.REVIEWED
    assert result.annotation.notes == "Keep these notes."
    assert result.annotation.fencer_names == ("Fencer One",)
    assert unit_of_work.commit_count == 1


def test_clear_label_clears_existing_relevance_label() -> None:
    existing = make_annotation(relevance_label="candidate")
    unit_of_work = make_unit_of_work(video=make_video(), annotation=existing)
    use_case = ClearAnnotationLabelUseCase(
        unit_of_work_factory=lambda: unit_of_work,
        clock=FixedClock(),
    )

    result = use_case.execute(ClearAnnotationLabelRequest(youtube_video_id="video-123"))

    assert result.changed is True
    assert result.annotation is not None
    assert result.annotation.relevance_label is None
    assert result.annotation.notes == existing.notes
    assert unit_of_work.commit_count == 1


def test_clear_label_does_not_create_annotation_when_missing() -> None:
    unit_of_work = make_unit_of_work(video=make_video())
    use_case = ClearAnnotationLabelUseCase(
        unit_of_work_factory=lambda: unit_of_work,
        clock=FixedClock(),
    )

    result = use_case.execute(ClearAnnotationLabelRequest(youtube_video_id="video-123"))

    assert result.changed is False
    assert result.annotation is None
    assert unit_of_work.annotations.get_by_youtube_id("video-123") is None
    assert unit_of_work.commit_count == 0


def test_failed_annotation_write_does_not_commit() -> None:
    unit_of_work = make_unit_of_work(video=make_video(), fail_on_save=True)
    use_case = SetAnnotationNotesUseCase(
        unit_of_work_factory=lambda: unit_of_work,
        clock=FixedClock(),
    )

    with pytest.raises(RepositoryError):
        use_case.execute(
            SetAnnotationNotesRequest(
                youtube_video_id="video-123",
                notes="Will fail.",
            )
        )

    assert unit_of_work.commit_count == 0
    assert unit_of_work.rollback_count == 1


def test_update_annotation_updates_multiple_fields_in_one_commit() -> None:
    existing = make_annotation(
        review_status=ReviewStatus.UNREVIEWED,
        notes="Keep old notes until replaced.",
        relevance_label="candidate",
    )
    unit_of_work = make_unit_of_work(video=make_video(), annotation=existing)
    use_case = UpdateAnnotationUseCase(
        unit_of_work_factory=lambda: unit_of_work,
        clock=FixedClock(),
    )

    result = use_case.execute(
        UpdateAnnotationRequest(
            youtube_video_id="video-123",
            review_status="reviewed",
            relevance_label="olympic-sabre-final",
            notes="Useful full sabre final footage.",
            update_review_status=True,
            update_relevance_label=True,
            update_notes=True,
        )
    )

    assert result.annotation.review_status is ReviewStatus.REVIEWED
    assert result.annotation.relevance_label == "olympic-sabre-final"
    assert result.annotation.notes == "Useful full sabre final footage."
    assert result.annotation.competition_name == existing.competition_name
    assert result.annotation.fencer_names == existing.fencer_names
    assert result.annotation.weapon_category == existing.weapon_category
    assert unit_of_work.annotations.saved == [result.annotation]
    assert unit_of_work.commit_count == 1


def test_update_annotation_creates_annotation_if_missing() -> None:
    unit_of_work = make_unit_of_work(video=make_video())
    use_case = UpdateAnnotationUseCase(
        unit_of_work_factory=lambda: unit_of_work,
        clock=FixedClock(),
    )

    result = use_case.execute(
        UpdateAnnotationRequest(
            youtube_video_id="video-123",
            review_status="reviewed",
            update_review_status=True,
        )
    )

    assert result.annotation.youtube_video_id == "video-123"
    assert result.annotation.review_status is ReviewStatus.REVIEWED
    assert result.annotation.relevance_label is None
    assert result.annotation.notes is None
    assert unit_of_work.commit_count == 1


def test_update_annotation_clears_label_when_null_or_empty_string() -> None:
    existing = make_annotation(relevance_label="candidate")
    unit_of_work = make_unit_of_work(video=make_video(), annotation=existing)
    use_case = UpdateAnnotationUseCase(
        unit_of_work_factory=lambda: unit_of_work,
        clock=FixedClock(),
    )

    first_result = use_case.execute(
        UpdateAnnotationRequest(
            youtube_video_id="video-123",
            relevance_label=None,
            update_relevance_label=True,
        )
    )
    second_result = use_case.execute(
        UpdateAnnotationRequest(
            youtube_video_id="video-123",
            relevance_label="   ",
            update_relevance_label=True,
        )
    )

    assert first_result.annotation.relevance_label is None
    assert second_result.annotation.relevance_label is None
    assert unit_of_work.commit_count == 2


def test_update_annotation_clears_notes_when_null_or_blank() -> None:
    existing = make_annotation(notes="Existing notes.")
    unit_of_work = make_unit_of_work(video=make_video(), annotation=existing)
    use_case = UpdateAnnotationUseCase(
        unit_of_work_factory=lambda: unit_of_work,
        clock=FixedClock(),
    )

    first_result = use_case.execute(
        UpdateAnnotationRequest(
            youtube_video_id="video-123",
            notes=None,
            update_notes=True,
        )
    )
    second_result = use_case.execute(
        UpdateAnnotationRequest(
            youtube_video_id="video-123",
            notes="   ",
            update_notes=True,
        )
    )

    assert first_result.annotation.notes is None
    assert second_result.annotation.notes is None
    assert unit_of_work.commit_count == 2


def test_update_annotation_rejects_empty_update() -> None:
    with pytest.raises(ValueError, match="at least one annotation field"):
        UpdateAnnotationRequest(youtube_video_id="video-123")


def test_update_annotation_raises_for_missing_video() -> None:
    unit_of_work = make_unit_of_work()
    use_case = UpdateAnnotationUseCase(
        unit_of_work_factory=lambda: unit_of_work,
        clock=FixedClock(),
    )

    with pytest.raises(AnnotationVideoNotFoundError) as error:
        use_case.execute(
            UpdateAnnotationRequest(
                youtube_video_id="missing-video",
                notes="Cannot save this.",
                update_notes=True,
            )
        )

    assert error.value.youtube_video_id == "missing-video"
    assert unit_of_work.commit_count == 0
