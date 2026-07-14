"""Tests for export CLI commands."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest
from pydantic import SecretStr
from typer.testing import CliRunner

from fencing_video_research_agent.application import (
    ExportVideosRequest,
    ExportVideosResult,
    InvalidExportFormatError,
)
from fencing_video_research_agent.infrastructure.settings import AppSettings
from fencing_video_research_agent.interface import cli
from fencing_video_research_agent.ports import ExportFileExistsError

runner = CliRunner()


@dataclass
class FakeExportVideosRuntime:
    """Fake export runtime returned by CLI bootstrap."""

    use_case: FakeExportVideosUseCase
    events: list[str]

    def close(self) -> None:
        self.events.append("close")


class FakeExportVideosUseCase:
    """Fake export use case for deterministic CLI tests."""

    def __init__(
        self,
        events: list[str],
        *,
        file_exists_path: Path | None = None,
    ) -> None:
        self.events = events
        self.file_exists_path = file_exists_path
        self.requests: list[ExportVideosRequest] = []

    def execute(self, request: ExportVideosRequest) -> ExportVideosResult:
        self.events.append("export-videos")
        self.requests.append(request)
        if self.file_exists_path is not None:
            raise ExportFileExistsError(self.file_exists_path)
        if request.export_format not in {"csv", "json"}:
            raise InvalidExportFormatError(request.export_format)
        output_path = request.output_path or Path(f"data/exports/videos.{request.export_format}")
        return ExportVideosResult(
            output_path=output_path,
            row_count=3,
            export_format=request.export_format,
        )


def fake_settings(database_url: str = "sqlite:///tmp/export.sqlite") -> AppSettings:
    """Return settings for export CLI tests."""

    return AppSettings.model_construct(
        youtube_api_key=SecretStr("export-secret-key"),
        database_url=database_url,
        log_level="INFO",
    )


def install_export_cli_fakes(
    monkeypatch: pytest.MonkeyPatch,
    *,
    file_exists_path: Path | None = None,
) -> tuple[list[str], FakeExportVideosRuntime]:
    """Replace export CLI dependencies with deterministic fakes."""

    events: list[str] = []
    runtime = FakeExportVideosRuntime(
        use_case=FakeExportVideosUseCase(events, file_exists_path=file_exists_path),
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

    def fake_build_export_videos_runtime(settings: AppSettings) -> FakeExportVideosRuntime:
        events.append(f"build-export:{settings.database_url}")
        return runtime

    def fail_collect_build(settings: AppSettings) -> object:
        raise AssertionError("export command must not build collection runtime")

    def fail_read_build(settings: AppSettings) -> object:
        raise AssertionError("export command must not build read-only runtime")

    def fail_annotation_build(settings: AppSettings) -> object:
        raise AssertionError("export command must not build annotation runtime")

    monkeypatch.setattr(cli, "load_settings", fake_load_settings)
    monkeypatch.setattr(cli, "ensure_database_current", fake_ensure_database_current)
    monkeypatch.setattr(cli, "build_export_videos_runtime", fake_build_export_videos_runtime)
    monkeypatch.setattr(cli, "build_collect_videos_runtime", fail_collect_build)
    monkeypatch.setattr(cli, "build_video_inspection_runtime", fail_read_build)
    monkeypatch.setattr(cli, "build_annotation_runtime", fail_annotation_build)
    return events, runtime


def test_export_videos_runs_migration_before_exporting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events, _runtime = install_export_cli_fakes(monkeypatch)

    result = runner.invoke(cli.app, ["export", "videos"])

    assert result.exit_code == 0
    assert events == [
        "settings:False",
        "migrate:sqlite:///tmp/export.sqlite",
        "build-export:sqlite:///tmp/export.sqlite",
        "export-videos",
        "close",
    ]


def test_export_videos_prints_only_summary(monkeypatch: pytest.MonkeyPatch) -> None:
    install_export_cli_fakes(monkeypatch)

    result = runner.invoke(cli.app, ["export", "videos", "--format", "json"])

    assert result.exit_code == 0
    assert "Export path: data/exports/videos.json" in result.output
    assert "Row count: 3" in result.output
    assert "Format: json" in result.output
    assert "Sabre final" not in result.output
    assert "export-secret-key" not in result.output


def test_export_videos_output_and_overwrite_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _events, runtime = install_export_cli_fakes(monkeypatch)

    result = runner.invoke(
        cli.app,
        [
            "export",
            "videos",
            "--format",
            "csv",
            "--output",
            "tmp/custom.csv",
            "--overwrite",
        ],
    )

    assert result.exit_code == 0
    assert runtime.use_case.requests[0] == ExportVideosRequest(
        export_format="csv",
        output_path=Path("tmp/custom.csv"),
        overwrite=True,
    )


def test_export_database_url_option_overrides_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events, _runtime = install_export_cli_fakes(monkeypatch)

    result = runner.invoke(
        cli.app,
        [
            "export",
            "videos",
            "--database-url",
            "sqlite:///tmp/override.sqlite",
        ],
    )

    assert result.exit_code == 0
    assert "migrate:sqlite:///tmp/override.sqlite" in events
    assert "build-export:sqlite:///tmp/override.sqlite" in events


def test_export_videos_does_not_require_youtube_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events, _runtime = install_export_cli_fakes(monkeypatch)

    result = runner.invoke(cli.app, ["export", "videos"])

    assert result.exit_code == 0
    assert "settings:False" in events


def test_export_videos_does_not_instantiate_other_runtimes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events, _runtime = install_export_cli_fakes(monkeypatch)

    result = runner.invoke(cli.app, ["export", "videos"])

    assert result.exit_code == 0
    assert not any(event.startswith("build:") for event in events)


def test_export_videos_rejects_unknown_format(monkeypatch: pytest.MonkeyPatch) -> None:
    install_export_cli_fakes(monkeypatch)

    result = runner.invoke(cli.app, ["export", "videos", "--format", "xlsx"])

    assert result.exit_code == 2
    assert "export format must be csv or json" in result.output
    assert "Traceback" not in result.output


def test_export_videos_reports_existing_output_without_overwrite(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_export_cli_fakes(monkeypatch, file_exists_path=Path("data/exports/videos.csv"))

    result = runner.invoke(cli.app, ["export", "videos"])

    assert result.exit_code == 3
    assert "Export file already exists: data\\exports\\videos.csv" in result.output or (
        "Export file already exists: data/exports/videos.csv" in result.output
    )
    assert "--overwrite" in result.output
    assert "Traceback" not in result.output
