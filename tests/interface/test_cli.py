"""Tests for the Typer command-line interface."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pytest
from pydantic import SecretStr
from typer.testing import CliRunner

from fencing_video_research_agent.application import CollectVideosRequest, CollectVideosResult
from fencing_video_research_agent.infrastructure.migrations import MigrationError
from fencing_video_research_agent.infrastructure.settings import AppSettings, ConfigurationError
from fencing_video_research_agent.interface import cli
from fencing_video_research_agent.ports import (
    PermanentYouTubeGatewayError,
    TransientYouTubeGatewayError,
)

runner = CliRunner()


@dataclass
class FakeRuntime:
    """Fake runtime returned by CLI bootstrap."""

    use_case: FakeUseCase
    closed: bool = False

    def close(self) -> None:
        self.closed = True


class FakeUseCase:
    """Fake collect use case for deterministic CLI tests."""

    def __init__(
        self,
        events: list[str],
        *,
        error: Exception | None = None,
    ) -> None:
        self.events = events
        self.error = error
        self.requests: list[CollectVideosRequest] = []

    def execute(self, request: CollectVideosRequest) -> CollectVideosResult:
        self.events.append("execute")
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        return CollectVideosResult(
            query_text=request.query_text,
            requested_max_results=request.max_results,
            search_result_count=3,
            unique_video_count=2,
            stored_video_count=2,
            search_hit_count=2,
            duplicate_search_result_count=1,
        )


def fake_settings(database_url: str = "sqlite:///tmp/research.sqlite") -> AppSettings:
    """Return settings without reading a real environment or env file."""

    return AppSettings.model_construct(
        youtube_api_key=SecretStr("test-api-key"),
        database_url=database_url,
        log_level="INFO",
    )


def install_cli_fakes(
    monkeypatch: pytest.MonkeyPatch,
    *,
    use_case_error: Exception | None = None,
    migration_error: Exception | None = None,
) -> tuple[list[str], FakeUseCase, FakeRuntime]:
    """Replace CLI dependencies with fakes and return their call records."""

    events: list[str] = []
    use_case = FakeUseCase(events, error=use_case_error)
    runtime = FakeRuntime(use_case=use_case)

    def fake_load_settings() -> AppSettings:
        events.append("settings")
        return fake_settings()

    def fake_ensure_database_current(database_url: str) -> None:
        events.append(f"migrate:{database_url}")
        if migration_error is not None:
            raise migration_error

    def fake_build_collect_videos_runtime(settings: AppSettings) -> FakeRuntime:
        events.append(f"build:{settings.database_url}")
        return runtime

    monkeypatch.setattr(cli, "load_settings", fake_load_settings)
    monkeypatch.setattr(cli, "ensure_database_current", fake_ensure_database_current)
    monkeypatch.setattr(cli, "build_collect_videos_runtime", fake_build_collect_videos_runtime)
    return events, use_case, runtime


def test_collect_calls_migration_before_use_case(monkeypatch: pytest.MonkeyPatch) -> None:
    events, _use_case, runtime = install_cli_fakes(monkeypatch)

    result = runner.invoke(cli.app, ["collect", "sabre fencing", "--max-results", "5"])

    assert result.exit_code == 0
    assert events == [
        "settings",
        "migrate:sqlite:///tmp/research.sqlite",
        "build:sqlite:///tmp/research.sqlite",
        "execute",
    ]
    assert runtime.closed is True


def test_collect_builds_request_with_query_and_max_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _events, use_case, _runtime = install_cli_fakes(monkeypatch)

    result = runner.invoke(cli.app, ["collect", " sabre final ", "--max-results", "7"])

    assert result.exit_code == 0
    request = use_case.requests[0]
    assert request.query_text == "sabre final"
    assert request.max_results == 7


def test_collect_passes_supported_search_parameters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _events, use_case, _runtime = install_cli_fakes(monkeypatch)

    result = runner.invoke(
        cli.app,
        [
            "collect",
            "sabre fencing",
            "--order",
            "date",
            "--published-after",
            "2026-01-01T00:00:00Z",
            "--published-before",
            "2026-02-01T00:00:00Z",
            "--region-code",
            "US",
        ],
    )

    assert result.exit_code == 0
    assert dict(use_case.requests[0].parameters) == {
        "order": "date",
        "publishedAfter": "2026-01-01T00:00:00Z",
        "publishedBefore": "2026-02-01T00:00:00Z",
        "regionCode": "US",
    }


def test_successful_collection_prints_useful_counts(monkeypatch: pytest.MonkeyPatch) -> None:
    install_cli_fakes(monkeypatch)

    result = runner.invoke(cli.app, ["collect", "sabre fencing"])

    assert result.exit_code == 0
    assert "Collection completed." in result.output
    assert "Requested max results: 5" in result.output
    assert "Search results returned: 3" in result.output
    assert "Unique videos: 2" in result.output
    assert "Duplicate search results skipped: 1" in result.output


def test_missing_youtube_api_key_returns_sanitized_configuration_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_load_settings() -> AppSettings:
        raise ConfigurationError("Missing or invalid configuration: YOUTUBE_API_KEY is required")

    monkeypatch.setattr(cli, "load_settings", fake_load_settings)

    result = runner.invoke(cli.app, ["collect", "sabre fencing"])

    assert result.exit_code == 1
    assert "Configuration error" in result.output
    assert "test-api-key" not in result.output


def test_transient_gateway_error_returns_safe_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_cli_fakes(
        monkeypatch,
        use_case_error=TransientYouTubeGatewayError("temporary outage"),
    )

    result = runner.invoke(cli.app, ["collect", "sabre fencing"])

    assert result.exit_code == 4
    assert "temporarily unavailable" in result.output


def test_permanent_gateway_error_returns_safe_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_cli_fakes(
        monkeypatch,
        use_case_error=PermanentYouTubeGatewayError("invalid search parameter"),
    )

    result = runner.invoke(cli.app, ["collect", "sabre fencing"])

    assert result.exit_code == 3
    assert "YouTube request failed" in result.output


def test_migration_failure_returns_safe_database_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_cli_fakes(monkeypatch, migration_error=MigrationError("Database migration failed"))

    result = runner.invoke(cli.app, ["collect", "sabre fencing"])

    assert result.exit_code == 5
    assert "Database operation failed" in result.output


def test_max_results_zero_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    install_cli_fakes(monkeypatch)

    result = runner.invoke(cli.app, ["collect", "sabre fencing", "--max-results", "0"])

    assert result.exit_code == 2


def test_max_results_above_cap_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    install_cli_fakes(monkeypatch)

    result = runner.invoke(cli.app, ["collect", "sabre fencing", "--max-results", "51"])

    assert result.exit_code == 2


def test_output_does_not_include_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    install_cli_fakes(monkeypatch)

    result = runner.invoke(cli.app, ["collect", "sabre fencing"])

    assert result.exit_code == 0
    assert "test-api-key" not in result.output


def test_database_url_option_overrides_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    events, _use_case, _runtime = install_cli_fakes(monkeypatch)

    result = runner.invoke(
        cli.app,
        ["collect", "sabre fencing", "--database-url", "sqlite:///tmp/override.sqlite"],
    )

    assert result.exit_code == 0
    assert "migrate:sqlite:///tmp/override.sqlite" in events
    assert "build:sqlite:///tmp/override.sqlite" in events


def test_normal_cli_tests_do_not_instantiate_real_google_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events, _use_case, _runtime = install_cli_fakes(monkeypatch)

    result = runner.invoke(cli.app, ["collect", "sabre fencing"])

    assert result.exit_code == 0
    assert "build:sqlite:///tmp/research.sqlite" in events


def test_application_and_domain_layers_do_not_import_infrastructure_dependencies() -> None:
    forbidden_pattern = re.compile(
        r"googleapiclient|sqlalchemy|alembic|YOUTUBE_API_KEY|dotenv|os\.environ"
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
