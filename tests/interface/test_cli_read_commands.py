"""Tests for read-only stored-video CLI commands."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import SecretStr
from typer.testing import CliRunner

from fencing_video_research_agent.application import (
    ListCollectionRunsRequest,
    ListCollectionRunsResult,
    ListStoredVideosRequest,
    ListStoredVideosResult,
    ShowCollectionRunRequest,
    ShowCollectionRunResult,
    ShowStoredVideoRequest,
    ShowStoredVideoResult,
    StoredCollectionRunNotFoundError,
    StoredVideoNotFoundError,
)
from fencing_video_research_agent.infrastructure.settings import AppSettings
from fencing_video_research_agent.interface import cli
from fencing_video_research_agent.ports import (
    CollectionRunRecordId,
    StoredCollectionRunDetail,
    StoredCollectionRunHit,
    StoredCollectionRunSummary,
    StoredVideoDetail,
    StoredVideoSummary,
)

runner = CliRunner()
NOW = datetime(2026, 7, 13, 8, 0, tzinfo=UTC)


def make_summary(youtube_video_id: str = "video-123") -> StoredVideoSummary:
    """Create a stored-video summary for CLI tests."""

    return StoredVideoSummary(
        youtube_video_id=youtube_video_id,
        title="Sabre final",
        channel_title="Fencing Channel",
        published_at=NOW,
        first_seen_at=NOW,
        last_refreshed_at=NOW,
    )


def make_detail(*, description: str = "A public fencing bout.") -> StoredVideoDetail:
    """Create stored-video detail for CLI tests."""

    return StoredVideoDetail(
        youtube_video_id="video-123",
        title="Sabre final",
        description=description,
        channel_id="channel-123",
        channel_title="Fencing Channel",
        published_at=NOW,
        duration_seconds=605,
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


def make_run_summary(run_id: int = 1) -> StoredCollectionRunSummary:
    """Create a collection-run summary for CLI tests."""

    return StoredCollectionRunSummary(
        run_id=CollectionRunRecordId(run_id),
        query_text="sabre fencing",
        status="completed",
        started_at=NOW,
        completed_at=NOW,
        hit_count=2,
    )


def make_run_detail(run_id: int = 1) -> StoredCollectionRunDetail:
    """Create collection-run detail for CLI tests."""

    return StoredCollectionRunDetail(
        run_id=CollectionRunRecordId(run_id),
        query_text="sabre fencing",
        query_parameters={"max_results": 2, "order": "date"},
        status="completed",
        started_at=NOW,
        completed_at=NOW,
        hit_count=2,
        hits=(
            StoredCollectionRunHit(
                rank=1,
                youtube_video_id="video-123",
                title="Sabre final",
                channel_title="Fencing Channel",
            ),
            StoredCollectionRunHit(
                rank=None,
                youtube_video_id="video-456",
                title="Sabre semifinal",
                channel_title="Fencing Archive",
            ),
        ),
    )


@dataclass
class FakeVideoInspectionRuntime:
    """Fake read-only runtime returned by CLI bootstrap."""

    list_videos: FakeListUseCase
    show_video: FakeShowUseCase
    list_collection_runs: FakeRunListUseCase
    show_collection_run: FakeRunShowUseCase
    events: list[str]

    def close(self) -> None:
        self.events.append("close")


class FakeListUseCase:
    """Fake list use case for deterministic CLI tests."""

    def __init__(
        self,
        events: list[str],
        *,
        videos: tuple[StoredVideoSummary, ...] = (),
    ) -> None:
        self.events = events
        self.videos = videos
        self.requests: list[ListStoredVideosRequest] = []

    def execute(self, request: ListStoredVideosRequest) -> ListStoredVideosResult:
        self.events.append("list")
        self.requests.append(request)
        return ListStoredVideosResult(videos=self.videos)


class FakeShowUseCase:
    """Fake show use case for deterministic CLI tests."""

    def __init__(
        self,
        events: list[str],
        *,
        detail: StoredVideoDetail | None = None,
    ) -> None:
        self.events = events
        self.detail = detail
        self.requests: list[ShowStoredVideoRequest] = []

    def execute(self, request: ShowStoredVideoRequest) -> ShowStoredVideoResult:
        self.events.append("show")
        self.requests.append(request)
        if self.detail is None:
            raise StoredVideoNotFoundError(request.youtube_video_id)
        return ShowStoredVideoResult(video=self.detail)


class FakeRunListUseCase:
    """Fake collection-run list use case for deterministic CLI tests."""

    def __init__(
        self,
        events: list[str],
        *,
        runs: tuple[StoredCollectionRunSummary, ...] = (),
    ) -> None:
        self.events = events
        self.runs = runs
        self.requests: list[ListCollectionRunsRequest] = []

    def execute(self, request: ListCollectionRunsRequest) -> ListCollectionRunsResult:
        self.events.append("runs-list")
        self.requests.append(request)
        return ListCollectionRunsResult(runs=self.runs)


class FakeRunShowUseCase:
    """Fake collection-run show use case for deterministic CLI tests."""

    def __init__(
        self,
        events: list[str],
        *,
        detail: StoredCollectionRunDetail | None = None,
    ) -> None:
        self.events = events
        self.detail = detail
        self.requests: list[ShowCollectionRunRequest] = []

    def execute(self, request: ShowCollectionRunRequest) -> ShowCollectionRunResult:
        self.events.append("runs-show")
        self.requests.append(request)
        if self.detail is None:
            raise StoredCollectionRunNotFoundError(request.run_id)
        return ShowCollectionRunResult(run=self.detail)


def fake_settings(database_url: str = "sqlite:///tmp/read.sqlite") -> AppSettings:
    """Return settings for read-only CLI tests."""

    return AppSettings.model_construct(
        youtube_api_key=SecretStr("read-secret-key"),
        database_url=database_url,
        log_level="INFO",
    )


def install_read_cli_fakes(
    monkeypatch: pytest.MonkeyPatch,
    *,
    videos: tuple[StoredVideoSummary, ...] = (),
    detail: StoredVideoDetail | None = None,
    runs: tuple[StoredCollectionRunSummary, ...] = (),
    run_detail: StoredCollectionRunDetail | None = None,
) -> tuple[list[str], FakeVideoInspectionRuntime]:
    """Replace read-only CLI dependencies with fakes."""

    events: list[str] = []
    list_use_case = FakeListUseCase(events, videos=videos)
    show_use_case = FakeShowUseCase(events, detail=detail)
    run_list_use_case = FakeRunListUseCase(events, runs=runs)
    run_show_use_case = FakeRunShowUseCase(events, detail=run_detail)
    runtime = FakeVideoInspectionRuntime(
        list_videos=list_use_case,
        show_video=show_use_case,
        list_collection_runs=run_list_use_case,
        show_collection_run=run_show_use_case,
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

    def fake_build_video_inspection_runtime(settings: AppSettings) -> FakeVideoInspectionRuntime:
        events.append(f"build-read:{settings.database_url}")
        return runtime

    def fail_collect_build(settings: AppSettings) -> object:
        raise AssertionError("read-only command must not build collection runtime")

    monkeypatch.setattr(cli, "load_settings", fake_load_settings)
    monkeypatch.setattr(cli, "ensure_database_current", fake_ensure_database_current)
    monkeypatch.setattr(cli, "build_video_inspection_runtime", fake_build_video_inspection_runtime)
    monkeypatch.setattr(cli, "build_collect_videos_runtime", fail_collect_build)
    return events, runtime


def test_videos_list_runs_migration_before_reading(monkeypatch: pytest.MonkeyPatch) -> None:
    events, _runtime = install_read_cli_fakes(monkeypatch, videos=(make_summary(),))

    result = runner.invoke(cli.app, ["videos", "list"])

    assert result.exit_code == 0
    assert events == [
        "settings:False",
        "migrate:sqlite:///tmp/read.sqlite",
        "build-read:sqlite:///tmp/read.sqlite",
        "list",
        "close",
    ]


def test_videos_list_prints_stored_video_summaries(monkeypatch: pytest.MonkeyPatch) -> None:
    install_read_cli_fakes(monkeypatch, videos=(make_summary(),))

    result = runner.invoke(cli.app, ["videos", "list"])

    assert result.exit_code == 0
    assert "Stored videos:" in result.output
    assert "video-123" in result.output
    assert "Sabre final" in result.output
    assert "Fencing Channel" in result.output
    assert "First seen:" in result.output
    assert "Last refreshed:" in result.output


def test_videos_list_handles_empty_database(monkeypatch: pytest.MonkeyPatch) -> None:
    install_read_cli_fakes(monkeypatch, videos=())

    result = runner.invoke(cli.app, ["videos", "list"])

    assert result.exit_code == 0
    assert "No stored videos found." in result.output


def test_videos_list_limit_zero_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    install_read_cli_fakes(monkeypatch)

    result = runner.invoke(cli.app, ["videos", "list", "--limit", "0"])

    assert result.exit_code == 2


def test_videos_list_limit_above_cap_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    install_read_cli_fakes(monkeypatch)

    result = runner.invoke(cli.app, ["videos", "list", "--limit", "101"])

    assert result.exit_code == 2


def test_videos_show_prints_stored_video_details(monkeypatch: pytest.MonkeyPatch) -> None:
    install_read_cli_fakes(monkeypatch, detail=make_detail())

    result = runner.invoke(cli.app, ["videos", "show", "video-123"])

    assert result.exit_code == 0
    assert "YouTube video ID: video-123" in result.output
    assert "Title: Sabre final" in result.output
    assert "Channel ID: channel-123" in result.output
    assert "Duration: 10:05" in result.output
    assert "Tags: sabre, final" in result.output
    assert "Annotation status: reviewed" in result.output


def test_videos_show_truncates_long_description(monkeypatch: pytest.MonkeyPatch) -> None:
    install_read_cli_fakes(monkeypatch, detail=make_detail(description="x" * 600))

    result = runner.invoke(cli.app, ["videos", "show", "video-123"])

    assert result.exit_code == 0
    assert f"Description: {'x' * 497}..." in result.output
    assert "x" * 600 not in result.output


def test_videos_show_missing_video_returns_safe_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_read_cli_fakes(monkeypatch, detail=None)

    result = runner.invoke(cli.app, ["videos", "show", "missing-video"])

    assert result.exit_code == 3
    assert "Stored video not found: missing-video" in result.output
    assert "Traceback" not in result.output


def test_database_url_option_overrides_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    events, _runtime = install_read_cli_fakes(monkeypatch, videos=(make_summary(),))

    result = runner.invoke(
        cli.app,
        ["videos", "list", "--database-url", "sqlite:///tmp/override.sqlite"],
    )

    assert result.exit_code == 0
    assert "migrate:sqlite:///tmp/override.sqlite" in events
    assert "build-read:sqlite:///tmp/override.sqlite" in events


def test_read_only_commands_do_not_require_youtube_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events, _runtime = install_read_cli_fakes(monkeypatch, videos=(make_summary(),))

    result = runner.invoke(cli.app, ["videos", "list"])

    assert result.exit_code == 0
    assert "settings:False" in events


def test_read_only_commands_do_not_instantiate_collection_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events, _runtime = install_read_cli_fakes(monkeypatch, videos=(make_summary(),))

    result = runner.invoke(cli.app, ["videos", "list"])

    assert result.exit_code == 0
    assert not any(event.startswith("build:") for event in events)


def test_read_only_output_does_not_expose_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_read_cli_fakes(monkeypatch, detail=make_detail())

    result = runner.invoke(cli.app, ["videos", "show", "video-123"])

    assert result.exit_code == 0
    assert "read-secret-key" not in result.output


def test_runs_list_runs_migration_before_reading(monkeypatch: pytest.MonkeyPatch) -> None:
    events, _runtime = install_read_cli_fakes(monkeypatch, runs=(make_run_summary(),))

    result = runner.invoke(cli.app, ["runs", "list"])

    assert result.exit_code == 0
    assert events == [
        "settings:False",
        "migrate:sqlite:///tmp/read.sqlite",
        "build-read:sqlite:///tmp/read.sqlite",
        "runs-list",
        "close",
    ]


def test_runs_list_prints_run_summaries(monkeypatch: pytest.MonkeyPatch) -> None:
    install_read_cli_fakes(monkeypatch, runs=(make_run_summary(),))

    result = runner.invoke(cli.app, ["runs", "list"])

    assert result.exit_code == 0
    assert "Collection runs:" in result.output
    assert "Run ID: 1" in result.output
    assert "Query: sabre fencing" in result.output
    assert "Status: completed" in result.output
    assert "Started:" in result.output
    assert "Completed:" in result.output
    assert "Hits: 2" in result.output


def test_runs_list_handles_empty_database(monkeypatch: pytest.MonkeyPatch) -> None:
    install_read_cli_fakes(monkeypatch, runs=())

    result = runner.invoke(cli.app, ["runs", "list"])

    assert result.exit_code == 0
    assert "No collection runs found." in result.output


def test_runs_list_limit_zero_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    install_read_cli_fakes(monkeypatch)

    result = runner.invoke(cli.app, ["runs", "list", "--limit", "0"])

    assert result.exit_code == 2


def test_runs_list_limit_above_cap_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    install_read_cli_fakes(monkeypatch)

    result = runner.invoke(cli.app, ["runs", "list", "--limit", "101"])

    assert result.exit_code == 2


def test_runs_show_prints_run_details_and_returned_videos(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_read_cli_fakes(monkeypatch, run_detail=make_run_detail())

    result = runner.invoke(cli.app, ["runs", "show", "1"])

    assert result.exit_code == 0
    assert "Run ID: 1" in result.output
    assert "Query: sabre fencing" in result.output
    assert "Query parameters: max_results=2, order=date" in result.output
    assert "Hit count: 2" in result.output
    assert "Returned videos:" in result.output
    assert "Rank: 1" in result.output
    assert "  YouTube video ID: video-123" in result.output
    assert "  Title: Sabre final" in result.output
    assert "  Channel: Fencing Channel" in result.output
    assert "Rank: not available" in result.output


def test_runs_show_missing_run_returns_safe_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_read_cli_fakes(monkeypatch, run_detail=None)

    result = runner.invoke(cli.app, ["runs", "show", "999"])

    assert result.exit_code == 3
    assert "Collection run not found: 999" in result.output
    assert "Traceback" not in result.output


def test_runs_show_rejects_non_positive_run_id(monkeypatch: pytest.MonkeyPatch) -> None:
    install_read_cli_fakes(monkeypatch)

    result = runner.invoke(cli.app, ["runs", "show", "0"])

    assert result.exit_code == 2


def test_runs_database_url_option_overrides_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    events, _runtime = install_read_cli_fakes(monkeypatch, runs=(make_run_summary(),))

    result = runner.invoke(
        cli.app,
        ["runs", "list", "--database-url", "sqlite:///tmp/override.sqlite"],
    )

    assert result.exit_code == 0
    assert "migrate:sqlite:///tmp/override.sqlite" in events
    assert "build-read:sqlite:///tmp/override.sqlite" in events


def test_run_commands_do_not_require_youtube_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events, _runtime = install_read_cli_fakes(monkeypatch, runs=(make_run_summary(),))

    result = runner.invoke(cli.app, ["runs", "list"])

    assert result.exit_code == 0
    assert "settings:False" in events


def test_run_commands_do_not_instantiate_collection_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events, _runtime = install_read_cli_fakes(monkeypatch, runs=(make_run_summary(),))

    result = runner.invoke(cli.app, ["runs", "list"])

    assert result.exit_code == 0
    assert not any(event.startswith("build:") for event in events)


def test_run_output_does_not_expose_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_read_cli_fakes(monkeypatch, run_detail=make_run_detail())

    result = runner.invoke(cli.app, ["runs", "show", "1"])

    assert result.exit_code == 0
    assert "read-secret-key" not in result.output


def test_application_and_domain_layers_do_not_import_forbidden_dependencies() -> None:
    forbidden_pattern = re.compile(
        r"googleapiclient|sqlalchemy|alembic|YOUTUBE_API_KEY|dotenv|os\.environ|secrets"
    )
    roots = [
        Path("src/fencing_video_research_agent/application"),
        Path("src/fencing_video_research_agent/domain"),
    ]

    matches: list[str] = []
    for root in roots:
        for path in root.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            if forbidden_pattern.search(text):
                matches.append(str(path))

    assert matches == []
