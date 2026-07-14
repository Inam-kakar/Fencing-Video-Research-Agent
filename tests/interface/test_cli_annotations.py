"""Tests for manual annotation CLI commands."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import pytest
from pydantic import SecretStr
from typer.testing import CliRunner

from fencing_video_research_agent.application import (
    AnnotationVideoNotFoundError,
    AnnotationWriteResult,
    ClearAnnotationLabelRequest,
    ClearAnnotationLabelResult,
    InvalidReviewStatusError,
    SetAnnotationLabelRequest,
    SetAnnotationNotesRequest,
    SetAnnotationReviewStatusRequest,
    ShowAnnotationRequest,
    ShowAnnotationResult,
)
from fencing_video_research_agent.domain import ResearchAnnotation, ReviewStatus
from fencing_video_research_agent.infrastructure.settings import AppSettings
from fencing_video_research_agent.interface import cli

runner = CliRunner()
NOW = datetime(2026, 7, 14, 9, 0, tzinfo=UTC)


def make_annotation(
    *,
    youtube_video_id: str = "video-123",
    review_status: ReviewStatus = ReviewStatus.REVIEWED,
    notes: str | None = "Useful sabre example.",
    relevance_label: str | None = "relevant",
) -> ResearchAnnotation:
    """Create an annotation for CLI output tests."""

    return ResearchAnnotation(
        youtube_video_id=youtube_video_id,
        updated_at=NOW,
        review_status=review_status,
        notes=notes,
        relevance_label=relevance_label,
        competition_name="European Championship",
        fencer_names=("Fencer One", "Fencer Two"),
        weapon_category="sabre",
        event_notes="Final bout",
    )


@dataclass
class FakeAnnotationRuntime:
    """Fake annotation runtime returned by CLI bootstrap."""

    show_annotation: FakeShowAnnotationUseCase
    set_review_status: FakeSetStatusUseCase
    set_notes: FakeSetNotesUseCase
    set_label: FakeSetLabelUseCase
    clear_label: FakeClearLabelUseCase
    events: list[str]

    def close(self) -> None:
        self.events.append("close")


class FakeShowAnnotationUseCase:
    """Fake show use case for deterministic CLI tests."""

    def __init__(
        self,
        events: list[str],
        *,
        annotation: ResearchAnnotation | None = None,
        missing_video: bool = False,
    ) -> None:
        self.events = events
        self.annotation = annotation
        self.missing_video = missing_video
        self.requests: list[ShowAnnotationRequest] = []

    def execute(self, request: ShowAnnotationRequest) -> ShowAnnotationResult:
        self.events.append("show-annotation")
        self.requests.append(request)
        if self.missing_video:
            raise AnnotationVideoNotFoundError(request.youtube_video_id)
        return ShowAnnotationResult(
            youtube_video_id=request.youtube_video_id,
            annotation=self.annotation,
        )


class FakeSetStatusUseCase:
    """Fake status update use case for deterministic CLI tests."""

    def __init__(self, events: list[str]) -> None:
        self.events = events
        self.requests: list[SetAnnotationReviewStatusRequest] = []

    def execute(self, request: SetAnnotationReviewStatusRequest) -> AnnotationWriteResult:
        self.events.append("set-status")
        self.requests.append(request)
        if request.status not in {status.value for status in ReviewStatus}:
            raise InvalidReviewStatusError(request.status)
        return AnnotationWriteResult(
            annotation=make_annotation(review_status=ReviewStatus(request.status)),
        )


class FakeSetNotesUseCase:
    """Fake notes update use case for deterministic CLI tests."""

    def __init__(self, events: list[str]) -> None:
        self.events = events
        self.requests: list[SetAnnotationNotesRequest] = []

    def execute(self, request: SetAnnotationNotesRequest) -> AnnotationWriteResult:
        self.events.append("set-notes")
        self.requests.append(request)
        return AnnotationWriteResult(annotation=make_annotation(notes=request.notes))


class FakeSetLabelUseCase:
    """Fake label update use case for deterministic CLI tests."""

    def __init__(self, events: list[str]) -> None:
        self.events = events
        self.requests: list[SetAnnotationLabelRequest] = []

    def execute(self, request: SetAnnotationLabelRequest) -> AnnotationWriteResult:
        self.events.append("set-label")
        self.requests.append(request)
        return AnnotationWriteResult(annotation=make_annotation(relevance_label=request.label))


class FakeClearLabelUseCase:
    """Fake clear-label use case for deterministic CLI tests."""

    def __init__(
        self,
        events: list[str],
        *,
        annotation: ResearchAnnotation | None = None,
        changed: bool = True,
    ) -> None:
        self.events = events
        self.annotation = annotation
        self.changed = changed
        self.requests: list[ClearAnnotationLabelRequest] = []

    def execute(self, request: ClearAnnotationLabelRequest) -> ClearAnnotationLabelResult:
        self.events.append("clear-label")
        self.requests.append(request)
        return ClearAnnotationLabelResult(
            youtube_video_id=request.youtube_video_id,
            annotation=self.annotation,
            changed=self.changed,
        )


def fake_settings(database_url: str = "sqlite:///tmp/annotations.sqlite") -> AppSettings:
    """Return settings for annotation CLI tests."""

    return AppSettings.model_construct(
        youtube_api_key=SecretStr("annotation-secret-key"),
        database_url=database_url,
        log_level="INFO",
    )


def install_annotation_cli_fakes(
    monkeypatch: pytest.MonkeyPatch,
    *,
    annotation: ResearchAnnotation | None = None,
    missing_video: bool = False,
    clear_annotation: ResearchAnnotation | None = None,
    clear_changed: bool = True,
) -> tuple[list[str], FakeAnnotationRuntime]:
    """Replace annotation CLI dependencies with deterministic fakes."""

    events: list[str] = []
    runtime = FakeAnnotationRuntime(
        show_annotation=FakeShowAnnotationUseCase(
            events,
            annotation=annotation,
            missing_video=missing_video,
        ),
        set_review_status=FakeSetStatusUseCase(events),
        set_notes=FakeSetNotesUseCase(events),
        set_label=FakeSetLabelUseCase(events),
        clear_label=FakeClearLabelUseCase(
            events,
            annotation=clear_annotation,
            changed=clear_changed,
        ),
        events=events,
    )

    def fake_load_settings(
        *,
        require_youtube_api_key: bool = True,
    ) -> AppSettings:
        events.append(f"settings:{require_youtube_api_key}")
        return fake_settings()

    def fake_ensure_database_current(database_url: str) -> None:
        events.append(f"migrate:{database_url}")

    def fake_build_annotation_runtime(settings: AppSettings) -> FakeAnnotationRuntime:
        events.append(f"build-annotations:{settings.database_url}")
        return runtime

    def fail_collect_build(settings: AppSettings) -> object:
        raise AssertionError("annotation command must not build collection runtime")

    def fail_read_build(settings: AppSettings) -> object:
        raise AssertionError("annotation command must not build read-only runtime")

    monkeypatch.setattr(cli, "load_settings", fake_load_settings)
    monkeypatch.setattr(cli, "ensure_database_current", fake_ensure_database_current)
    monkeypatch.setattr(cli, "build_annotation_runtime", fake_build_annotation_runtime)
    monkeypatch.setattr(cli, "build_collect_videos_runtime", fail_collect_build)
    monkeypatch.setattr(cli, "build_video_inspection_runtime", fail_read_build)
    return events, runtime


def test_annotations_show_runs_migration_before_reading(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events, _runtime = install_annotation_cli_fakes(monkeypatch)

    result = runner.invoke(cli.app, ["annotations", "show", "video-123"])

    assert result.exit_code == 0
    assert events == [
        "settings:False",
        "migrate:sqlite:///tmp/annotations.sqlite",
        "build-annotations:sqlite:///tmp/annotations.sqlite",
        "show-annotation",
        "close",
    ]


def test_annotations_show_prints_no_annotation_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_annotation_cli_fakes(monkeypatch, annotation=None)

    result = runner.invoke(cli.app, ["annotations", "show", "video-123"])

    assert result.exit_code == 0
    assert "YouTube video ID: video-123" in result.output
    assert "No annotation recorded yet." in result.output


def test_annotations_show_prints_existing_annotation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_annotation_cli_fakes(monkeypatch, annotation=make_annotation())

    result = runner.invoke(cli.app, ["annotations", "show", "video-123"])

    assert result.exit_code == 0
    assert "Review status: reviewed" in result.output
    assert "Notes: Useful sabre example." in result.output
    assert "Relevance label: relevant" in result.output
    assert "Competition name: European Championship" in result.output
    assert "Fencer names: Fencer One, Fencer Two" in result.output
    assert "Weapon category: sabre" in result.output
    assert "Event notes: Final bout" in result.output
    assert "Updated at: 2026-07-14 09:00:00+00:00" in result.output


def test_annotations_show_missing_video_returns_safe_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_annotation_cli_fakes(monkeypatch, missing_video=True)

    result = runner.invoke(cli.app, ["annotations", "show", "missing-video"])

    assert result.exit_code == 3
    assert "Stored video not found: missing-video" in result.output
    assert "Traceback" not in result.output


def test_set_status_prints_success(monkeypatch: pytest.MonkeyPatch) -> None:
    install_annotation_cli_fakes(monkeypatch)

    result = runner.invoke(
        cli.app,
        ["annotations", "set-status", "video-123", "reviewed"],
    )

    assert result.exit_code == 0
    assert "Annotation review status updated." in result.output
    assert "YouTube video ID: video-123" in result.output
    assert "Review status: reviewed" in result.output


def test_set_status_rejects_invalid_status(monkeypatch: pytest.MonkeyPatch) -> None:
    install_annotation_cli_fakes(monkeypatch)

    result = runner.invoke(
        cli.app,
        ["annotations", "set-status", "video-123", "relevant"],
    )

    assert result.exit_code == 2
    assert "invalid review status: relevant" in result.output
    assert "unreviewed" in result.output
    assert "reviewed" in result.output
    assert "Traceback" not in result.output


def test_set_notes_prints_success_without_echoing_long_notes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_annotation_cli_fakes(monkeypatch)
    notes = "x" * 600

    result = runner.invoke(
        cli.app,
        ["annotations", "set-notes", "video-123", "--notes", notes],
    )

    assert result.exit_code == 0
    assert "Annotation notes updated." in result.output
    assert "YouTube video ID: video-123" in result.output
    assert notes not in result.output


def test_set_label_prints_single_label_success(monkeypatch: pytest.MonkeyPatch) -> None:
    install_annotation_cli_fakes(monkeypatch)

    result = runner.invoke(
        cli.app,
        ["annotations", "set-label", "video-123", "gold-medal"],
    )

    assert result.exit_code == 0
    assert "Annotation relevance label updated." in result.output
    assert "Relevance label: gold-medal" in result.output


def test_clear_label_prints_success(monkeypatch: pytest.MonkeyPatch) -> None:
    install_annotation_cli_fakes(
        monkeypatch,
        clear_annotation=make_annotation(relevance_label=None),
        clear_changed=True,
    )

    result = runner.invoke(cli.app, ["annotations", "clear-label", "video-123"])

    assert result.exit_code == 0
    assert "Annotation relevance label cleared." in result.output
    assert "YouTube video ID: video-123" in result.output


def test_clear_label_without_annotation_prints_friendly_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_annotation_cli_fakes(monkeypatch, clear_annotation=None, clear_changed=False)

    result = runner.invoke(cli.app, ["annotations", "clear-label", "video-123"])

    assert result.exit_code == 0
    assert "No annotation recorded yet; relevance label is already clear." in result.output
    assert "YouTube video ID: video-123" in result.output


def test_annotation_commands_do_not_require_youtube_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events, _runtime = install_annotation_cli_fakes(monkeypatch)

    result = runner.invoke(cli.app, ["annotations", "show", "video-123"])

    assert result.exit_code == 0
    assert "settings:False" in events


def test_annotation_commands_do_not_instantiate_other_runtimes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events, _runtime = install_annotation_cli_fakes(monkeypatch)

    result = runner.invoke(cli.app, ["annotations", "set-label", "video-123", "review"])

    assert result.exit_code == 0
    assert not any(event.startswith("build:") for event in events)


def test_annotation_database_url_option_overrides_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events, _runtime = install_annotation_cli_fakes(monkeypatch)

    result = runner.invoke(
        cli.app,
        [
            "annotations",
            "show",
            "video-123",
            "--database-url",
            "sqlite:///tmp/override.sqlite",
        ],
    )

    assert result.exit_code == 0
    assert "migrate:sqlite:///tmp/override.sqlite" in events
    assert "build-annotations:sqlite:///tmp/override.sqlite" in events
    assert "annotation-secret-key" not in result.output
