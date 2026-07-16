"""Application use cases for manual researcher annotations."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace

from fencing_video_research_agent.domain import ResearchAnnotation, ReviewStatus
from fencing_video_research_agent.ports import Clock, UnitOfWork

type UnitOfWorkFactory = Callable[[], UnitOfWork]

MAX_RELEVANCE_LABEL_LENGTH = 100


@dataclass(frozen=True, slots=True)
class ShowAnnotationRequest:
    """Input for inspecting a stored video's researcher annotation."""

    youtube_video_id: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "youtube_video_id", _require_youtube_video_id(self.youtube_video_id)
        )


@dataclass(frozen=True, slots=True)
class ShowAnnotationResult:
    """Annotation details for one stored video."""

    youtube_video_id: str
    annotation: ResearchAnnotation | None


@dataclass(frozen=True, slots=True)
class SetAnnotationReviewStatusRequest:
    """Input for updating one annotation review status."""

    youtube_video_id: str
    status: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "youtube_video_id", _require_youtube_video_id(self.youtube_video_id)
        )
        object.__setattr__(self, "status", self.status.strip())


@dataclass(frozen=True, slots=True)
class SetAnnotationNotesRequest:
    """Input for updating researcher notes."""

    youtube_video_id: str
    notes: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "youtube_video_id", _require_youtube_video_id(self.youtube_video_id)
        )


@dataclass(frozen=True, slots=True)
class SetAnnotationLabelRequest:
    """Input for updating the single relevance label."""

    youtube_video_id: str
    label: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "youtube_video_id", _require_youtube_video_id(self.youtube_video_id)
        )
        object.__setattr__(self, "label", _require_relevance_label(self.label))


@dataclass(frozen=True, slots=True)
class ClearAnnotationLabelRequest:
    """Input for clearing the single relevance label."""

    youtube_video_id: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "youtube_video_id", _require_youtube_video_id(self.youtube_video_id)
        )


@dataclass(frozen=True, slots=True)
class UpdateAnnotationRequest:
    """Input for updating browser-editable annotation fields in one transaction."""

    youtube_video_id: str
    review_status: str | None = None
    relevance_label: str | None = None
    notes: str | None = None
    update_review_status: bool = False
    update_relevance_label: bool = False
    update_notes: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "youtube_video_id", _require_youtube_video_id(self.youtube_video_id)
        )
        if not (self.update_review_status or self.update_relevance_label or self.update_notes):
            msg = "at least one annotation field must be provided"
            raise ValueError(msg)
        if self.update_review_status and self.review_status is None:
            msg = "review_status must not be null"
            raise ValueError(msg)
        if self.review_status is not None:
            object.__setattr__(self, "review_status", self.review_status.strip())


@dataclass(frozen=True, slots=True)
class AnnotationWriteResult:
    """Result for annotation commands that persist a row."""

    annotation: ResearchAnnotation


@dataclass(frozen=True, slots=True)
class ClearAnnotationLabelResult:
    """Result for clearing a relevance label."""

    youtube_video_id: str
    annotation: ResearchAnnotation | None
    changed: bool


class AnnotationVideoNotFoundError(Exception):
    """Raised when an annotation command targets an unknown stored video."""

    def __init__(self, youtube_video_id: str) -> None:
        self.youtube_video_id = youtube_video_id
        super().__init__(f"stored video not found: {youtube_video_id}")


class InvalidReviewStatusError(ValueError):
    """Raised when an annotation status is not a known ReviewStatus value."""

    def __init__(self, status: str) -> None:
        self.status = status
        expected = ", ".join(status.value for status in ReviewStatus)
        super().__init__(f"invalid review status: {status}. Expected one of: {expected}")


class ShowAnnotationUseCase:
    """Show one stored video's manual research annotation."""

    def __init__(self, *, unit_of_work_factory: UnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    def execute(self, request: ShowAnnotationRequest) -> ShowAnnotationResult:
        """Return an annotation if the target video exists."""

        with self._unit_of_work_factory() as unit_of_work:
            _require_video_exists(unit_of_work, request.youtube_video_id)
            annotation = unit_of_work.annotations.get_by_youtube_id(request.youtube_video_id)
        return ShowAnnotationResult(
            youtube_video_id=request.youtube_video_id,
            annotation=annotation,
        )


class SetAnnotationReviewStatusUseCase:
    """Create or update an annotation review status."""

    def __init__(self, *, unit_of_work_factory: UnitOfWorkFactory, clock: Clock) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock

    def execute(self, request: SetAnnotationReviewStatusRequest) -> AnnotationWriteResult:
        """Update only the review status while preserving other annotation fields."""

        review_status = _parse_review_status(request.status)
        with self._unit_of_work_factory() as unit_of_work:
            _require_video_exists(unit_of_work, request.youtube_video_id)
            annotation = _annotation_or_default(
                unit_of_work.annotations.get_by_youtube_id(request.youtube_video_id),
                youtube_video_id=request.youtube_video_id,
                clock=self._clock,
            )
            updated = replace(
                annotation,
                review_status=review_status,
                updated_at=self._clock.utcnow(),
            )
            unit_of_work.annotations.save(updated)
            unit_of_work.commit()
        return AnnotationWriteResult(annotation=updated)


class SetAnnotationNotesUseCase:
    """Create or update researcher notes."""

    def __init__(self, *, unit_of_work_factory: UnitOfWorkFactory, clock: Clock) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock

    def execute(self, request: SetAnnotationNotesRequest) -> AnnotationWriteResult:
        """Update only notes while preserving other annotation fields."""

        with self._unit_of_work_factory() as unit_of_work:
            _require_video_exists(unit_of_work, request.youtube_video_id)
            annotation = _annotation_or_default(
                unit_of_work.annotations.get_by_youtube_id(request.youtube_video_id),
                youtube_video_id=request.youtube_video_id,
                clock=self._clock,
            )
            updated = replace(
                annotation,
                notes=_notes_value(request.notes),
                updated_at=self._clock.utcnow(),
            )
            unit_of_work.annotations.save(updated)
            unit_of_work.commit()
        return AnnotationWriteResult(annotation=updated)


class SetAnnotationLabelUseCase:
    """Create or update the single relevance label."""

    def __init__(self, *, unit_of_work_factory: UnitOfWorkFactory, clock: Clock) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock

    def execute(self, request: SetAnnotationLabelRequest) -> AnnotationWriteResult:
        """Update only the relevance label while preserving other annotation fields."""

        with self._unit_of_work_factory() as unit_of_work:
            _require_video_exists(unit_of_work, request.youtube_video_id)
            annotation = _annotation_or_default(
                unit_of_work.annotations.get_by_youtube_id(request.youtube_video_id),
                youtube_video_id=request.youtube_video_id,
                clock=self._clock,
            )
            updated = replace(
                annotation,
                relevance_label=request.label,
                updated_at=self._clock.utcnow(),
            )
            unit_of_work.annotations.save(updated)
            unit_of_work.commit()
        return AnnotationWriteResult(annotation=updated)


class ClearAnnotationLabelUseCase:
    """Clear the single relevance label for an existing annotation."""

    def __init__(self, *, unit_of_work_factory: UnitOfWorkFactory, clock: Clock) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock

    def execute(self, request: ClearAnnotationLabelRequest) -> ClearAnnotationLabelResult:
        """Clear only relevance_label, committing only when a stored annotation changes."""

        with self._unit_of_work_factory() as unit_of_work:
            _require_video_exists(unit_of_work, request.youtube_video_id)
            annotation = unit_of_work.annotations.get_by_youtube_id(request.youtube_video_id)
            if annotation is None:
                return ClearAnnotationLabelResult(
                    youtube_video_id=request.youtube_video_id,
                    annotation=None,
                    changed=False,
                )
            if annotation.relevance_label is None:
                return ClearAnnotationLabelResult(
                    youtube_video_id=request.youtube_video_id,
                    annotation=annotation,
                    changed=False,
                )

            updated = replace(annotation, relevance_label=None, updated_at=self._clock.utcnow())
            unit_of_work.annotations.save(updated)
            unit_of_work.commit()

        return ClearAnnotationLabelResult(
            youtube_video_id=request.youtube_video_id,
            annotation=updated,
            changed=True,
        )


class UpdateAnnotationUseCase:
    """Update browser-editable annotation fields in one atomic write."""

    def __init__(self, *, unit_of_work_factory: UnitOfWorkFactory, clock: Clock) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock

    def execute(self, request: UpdateAnnotationRequest) -> AnnotationWriteResult:
        """Update only requested fields while preserving all other annotation data."""

        review_status = (
            _parse_review_status(request.review_status)
            if request.update_review_status and request.review_status is not None
            else None
        )
        relevance_label = (
            _optional_relevance_label(request.relevance_label)
            if request.update_relevance_label
            else None
        )
        notes = _optional_notes_value(request.notes) if request.update_notes else None

        with self._unit_of_work_factory() as unit_of_work:
            _require_video_exists(unit_of_work, request.youtube_video_id)
            annotation = _annotation_or_default(
                unit_of_work.annotations.get_by_youtube_id(request.youtube_video_id),
                youtube_video_id=request.youtube_video_id,
                clock=self._clock,
            )
            next_review_status = annotation.review_status
            if request.update_review_status and review_status is not None:
                next_review_status = review_status
            next_relevance_label = annotation.relevance_label
            if request.update_relevance_label:
                next_relevance_label = relevance_label
            next_notes = annotation.notes
            if request.update_notes:
                next_notes = notes

            updated = replace(
                annotation,
                review_status=next_review_status,
                relevance_label=next_relevance_label,
                notes=next_notes,
                updated_at=self._clock.utcnow(),
            )
            unit_of_work.annotations.save(updated)
            unit_of_work.commit()
        return AnnotationWriteResult(annotation=updated)


def _require_youtube_video_id(youtube_video_id: str) -> str:
    value = youtube_video_id.strip()
    if not value:
        msg = "youtube_video_id must not be empty"
        raise ValueError(msg)
    return value


def _require_relevance_label(label: str) -> str:
    value = label.strip()
    if not value:
        msg = "label must not be empty"
        raise ValueError(msg)
    if len(value) > MAX_RELEVANCE_LABEL_LENGTH:
        msg = f"label must be at most {MAX_RELEVANCE_LABEL_LENGTH} characters"
        raise ValueError(msg)
    return value


def _optional_relevance_label(label: str | None) -> str | None:
    if label is None:
        return None
    value = label.strip()
    if not value:
        return None
    if len(value) > MAX_RELEVANCE_LABEL_LENGTH:
        msg = f"label must be at most {MAX_RELEVANCE_LABEL_LENGTH} characters"
        raise ValueError(msg)
    return value


def _notes_value(notes: str) -> str | None:
    if not notes.strip():
        return None
    return notes


def _optional_notes_value(notes: str | None) -> str | None:
    if notes is None or not notes.strip():
        return None
    return notes


def _parse_review_status(status: str) -> ReviewStatus:
    try:
        return ReviewStatus(status)
    except ValueError as exc:
        raise InvalidReviewStatusError(status) from exc


def _require_video_exists(unit_of_work: UnitOfWork, youtube_video_id: str) -> None:
    if unit_of_work.videos.get_by_youtube_id(youtube_video_id) is None:
        raise AnnotationVideoNotFoundError(youtube_video_id)


def _annotation_or_default(
    annotation: ResearchAnnotation | None,
    *,
    youtube_video_id: str,
    clock: Clock,
) -> ResearchAnnotation:
    if annotation is not None:
        return annotation
    return ResearchAnnotation(youtube_video_id=youtube_video_id, updated_at=clock.utcnow())
