"""Tests for the application composition root."""

from __future__ import annotations

from dataclasses import dataclass

import pytest
from pydantic import SecretStr

from fencing_video_research_agent import bootstrap
from fencing_video_research_agent.infrastructure.settings import AppSettings


@dataclass
class FakeEngine:
    """Tiny fake SQLAlchemy engine for bootstrap wiring tests."""

    disposed: bool = False

    def dispose(self) -> None:
        self.disposed = True


class FakeGateway:
    """Fake YouTube gateway used only to verify bootstrap wiring."""

    def __init__(self, *, client: object, clock: object) -> None:
        self.client = client
        self.clock = clock


def test_build_collect_videos_runtime_wires_infrastructure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    fake_client = object()
    fake_engine = FakeEngine()
    fake_session_factory = object()

    settings = AppSettings.model_construct(
        youtube_api_key=SecretStr("test-api-key"),
        database_url="sqlite:///tmp/research.sqlite",
        log_level="INFO",
    )

    def fake_create_client(api_key: SecretStr) -> object:
        calls.append(f"client:{api_key.get_secret_value()}")
        return fake_client

    def fake_create_engine(database_url: str) -> FakeEngine:
        calls.append(f"engine:{database_url}")
        return fake_engine

    def fake_create_session_factory(engine: FakeEngine) -> object:
        calls.append(f"session:{engine is fake_engine}")
        return fake_session_factory

    monkeypatch.setattr(bootstrap, "create_youtube_data_api_client", fake_create_client)
    monkeypatch.setattr(bootstrap, "create_database_engine", fake_create_engine)
    monkeypatch.setattr(bootstrap, "create_session_factory", fake_create_session_factory)
    monkeypatch.setattr(bootstrap, "YouTubeDataApiGateway", FakeGateway)

    runtime = bootstrap.build_collect_videos_runtime(settings)

    assert calls == [
        "client:test-api-key",
        "engine:sqlite:///tmp/research.sqlite",
        "session:True",
    ]
    assert runtime.use_case is not None

    runtime.close()

    assert fake_engine.disposed is True


def test_build_video_inspection_runtime_does_not_create_youtube_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    fake_engine = FakeEngine()
    fake_session_factory = object()

    settings = AppSettings.model_construct(
        youtube_api_key=SecretStr(""),
        database_url="sqlite:///tmp/research.sqlite",
        log_level="INFO",
    )

    def fake_create_client(api_key: SecretStr) -> object:
        raise AssertionError("inspection runtime must not create YouTube clients")

    def fake_create_engine(database_url: str) -> FakeEngine:
        calls.append(f"engine:{database_url}")
        return fake_engine

    def fake_create_session_factory(engine: FakeEngine) -> object:
        calls.append(f"session:{engine is fake_engine}")
        return fake_session_factory

    monkeypatch.setattr(bootstrap, "create_youtube_data_api_client", fake_create_client)
    monkeypatch.setattr(bootstrap, "create_database_engine", fake_create_engine)
    monkeypatch.setattr(bootstrap, "create_session_factory", fake_create_session_factory)

    runtime = bootstrap.build_video_inspection_runtime(settings)

    assert calls == [
        "engine:sqlite:///tmp/research.sqlite",
        "session:True",
    ]
    assert runtime.list_videos is not None
    assert runtime.show_video is not None
    assert runtime.list_collection_runs is not None
    assert runtime.show_collection_run is not None

    runtime.close()

    assert fake_engine.disposed is True


def test_build_api_runtime_does_not_create_youtube_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    fake_engine = FakeEngine()
    fake_session_factory = object()

    settings = AppSettings.model_construct(
        youtube_api_key=SecretStr(""),
        database_url="sqlite:///tmp/research.sqlite",
        log_level="INFO",
    )

    def fake_create_client(api_key: SecretStr) -> object:
        raise AssertionError("API runtime must not create YouTube clients")

    def fake_create_engine(database_url: str) -> FakeEngine:
        calls.append(f"engine:{database_url}")
        return fake_engine

    def fake_create_session_factory(engine: FakeEngine) -> object:
        calls.append(f"session:{engine is fake_engine}")
        return fake_session_factory

    monkeypatch.setattr(bootstrap, "create_youtube_data_api_client", fake_create_client)
    monkeypatch.setattr(bootstrap, "create_database_engine", fake_create_engine)
    monkeypatch.setattr(bootstrap, "create_session_factory", fake_create_session_factory)

    runtime = bootstrap.build_api_runtime(settings)

    assert calls == [
        "engine:sqlite:///tmp/research.sqlite",
        "session:True",
    ]
    assert runtime.summary is not None
    assert runtime.list_video_table_rows is not None
    assert runtime.show_video is not None
    assert runtime.update_annotation is not None
    assert runtime.collect_videos is None
    assert runtime.list_collection_runs is not None
    assert runtime.show_collection_run is not None
    assert runtime.list_search_hit_table_rows is not None

    runtime.close()

    assert fake_engine.disposed is True


def test_build_api_runtime_wires_collection_when_youtube_key_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    fake_client = object()
    fake_engine = FakeEngine()
    fake_session_factory = object()

    settings = AppSettings.model_construct(
        youtube_api_key=SecretStr("test-api-key"),
        database_url="sqlite:///tmp/research.sqlite",
        log_level="INFO",
    )

    def fake_create_client(api_key: SecretStr) -> object:
        calls.append(f"client:{api_key.get_secret_value()}")
        return fake_client

    def fake_create_engine(database_url: str) -> FakeEngine:
        calls.append(f"engine:{database_url}")
        return fake_engine

    def fake_create_session_factory(engine: FakeEngine) -> object:
        calls.append(f"session:{engine is fake_engine}")
        return fake_session_factory

    monkeypatch.setattr(bootstrap, "create_youtube_data_api_client", fake_create_client)
    monkeypatch.setattr(bootstrap, "create_database_engine", fake_create_engine)
    monkeypatch.setattr(bootstrap, "create_session_factory", fake_create_session_factory)
    monkeypatch.setattr(bootstrap, "YouTubeDataApiGateway", FakeGateway)

    runtime = bootstrap.build_api_runtime(settings)

    assert calls == [
        "engine:sqlite:///tmp/research.sqlite",
        "session:True",
        "client:test-api-key",
    ]
    assert runtime.collect_videos is not None

    runtime.close()

    assert fake_engine.disposed is True


def test_build_annotation_runtime_does_not_create_youtube_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    fake_engine = FakeEngine()
    fake_session_factory = object()

    settings = AppSettings.model_construct(
        youtube_api_key=SecretStr(""),
        database_url="sqlite:///tmp/research.sqlite",
        log_level="INFO",
    )

    def fake_create_client(api_key: SecretStr) -> object:
        raise AssertionError("annotation runtime must not create YouTube clients")

    def fake_create_engine(database_url: str) -> FakeEngine:
        calls.append(f"engine:{database_url}")
        return fake_engine

    def fake_create_session_factory(engine: FakeEngine) -> object:
        calls.append(f"session:{engine is fake_engine}")
        return fake_session_factory

    monkeypatch.setattr(bootstrap, "create_youtube_data_api_client", fake_create_client)
    monkeypatch.setattr(bootstrap, "create_database_engine", fake_create_engine)
    monkeypatch.setattr(bootstrap, "create_session_factory", fake_create_session_factory)

    runtime = bootstrap.build_annotation_runtime(settings)

    assert calls == [
        "engine:sqlite:///tmp/research.sqlite",
        "session:True",
    ]
    assert runtime.show_annotation is not None
    assert runtime.set_review_status is not None
    assert runtime.set_notes is not None
    assert runtime.set_label is not None
    assert runtime.clear_label is not None

    runtime.close()

    assert fake_engine.disposed is True


def test_build_export_videos_runtime_does_not_create_youtube_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    fake_engine = FakeEngine()
    fake_session_factory = object()

    settings = AppSettings.model_construct(
        youtube_api_key=SecretStr(""),
        database_url="sqlite:///tmp/research.sqlite",
        log_level="INFO",
    )

    def fake_create_client(api_key: SecretStr) -> object:
        raise AssertionError("export runtime must not create YouTube clients")

    def fake_create_engine(database_url: str) -> FakeEngine:
        calls.append(f"engine:{database_url}")
        return fake_engine

    def fake_create_session_factory(engine: FakeEngine) -> object:
        calls.append(f"session:{engine is fake_engine}")
        return fake_session_factory

    monkeypatch.setattr(bootstrap, "create_youtube_data_api_client", fake_create_client)
    monkeypatch.setattr(bootstrap, "create_database_engine", fake_create_engine)
    monkeypatch.setattr(bootstrap, "create_session_factory", fake_create_session_factory)

    runtime = bootstrap.build_export_videos_runtime(settings)

    assert calls == [
        "engine:sqlite:///tmp/research.sqlite",
        "session:True",
    ]
    assert runtime.use_case is not None

    runtime.close()

    assert fake_engine.disposed is True


def test_build_export_search_hits_runtime_does_not_create_youtube_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    fake_engine = FakeEngine()
    fake_session_factory = object()

    settings = AppSettings.model_construct(
        youtube_api_key=SecretStr(""),
        database_url="sqlite:///tmp/research.sqlite",
        log_level="INFO",
    )

    def fake_create_client(api_key: SecretStr) -> object:
        raise AssertionError("search-hit export runtime must not create YouTube clients")

    def fake_create_engine(database_url: str) -> FakeEngine:
        calls.append(f"engine:{database_url}")
        return fake_engine

    def fake_create_session_factory(engine: FakeEngine) -> object:
        calls.append(f"session:{engine is fake_engine}")
        return fake_session_factory

    monkeypatch.setattr(bootstrap, "create_youtube_data_api_client", fake_create_client)
    monkeypatch.setattr(bootstrap, "create_database_engine", fake_create_engine)
    monkeypatch.setattr(bootstrap, "create_session_factory", fake_create_session_factory)

    runtime = bootstrap.build_export_search_hits_runtime(settings)

    assert calls == [
        "engine:sqlite:///tmp/research.sqlite",
        "session:True",
    ]
    assert runtime.use_case is not None

    runtime.close()

    assert fake_engine.disposed is True
