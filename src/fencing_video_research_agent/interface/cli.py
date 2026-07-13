"""Typer command-line interface for controlled metadata collection."""

from __future__ import annotations

from typing import Annotated

import typer

from fencing_video_research_agent.application import (
    CollectVideosRequest,
    CollectVideosResult,
    MissingYouTubeMetadataError,
)
from fencing_video_research_agent.bootstrap import (
    CollectVideosRuntime,
    build_collect_videos_runtime,
)
from fencing_video_research_agent.infrastructure.migrations import (
    MigrationError,
    ensure_database_current,
)
from fencing_video_research_agent.infrastructure.settings import (
    ConfigurationError,
    load_settings,
)
from fencing_video_research_agent.ports import (
    PermanentYouTubeGatewayError,
    RepositoryError,
    TransientYouTubeGatewayError,
)

MAX_COLLECT_RESULTS = 50

app = typer.Typer(
    help="Collect and organize public fencing-video metadata.",
    no_args_is_help=True,
    invoke_without_command=False,
)


@app.callback()
def main() -> None:
    """Collect and organize public fencing-video metadata."""


@app.command()
def collect(
    query: Annotated[str, typer.Argument(help="YouTube search query.")],
    max_results: Annotated[
        int,
        typer.Option(
            "--max-results",
            min=1,
            max=MAX_COLLECT_RESULTS,
            help="Maximum videos to collect. Capped at 50 for the first CLI.",
        ),
    ] = 5,
    order: Annotated[str | None, typer.Option("--order", help="YouTube search order.")] = None,
    published_after: Annotated[
        str | None,
        typer.Option("--published-after", help="Only videos published after this timestamp."),
    ] = None,
    published_before: Annotated[
        str | None,
        typer.Option("--published-before", help="Only videos published before this timestamp."),
    ] = None,
    region_code: Annotated[
        str | None,
        typer.Option("--region-code", help="Two-letter YouTube region code."),
    ] = None,
    database_url: Annotated[
        str | None,
        typer.Option("--database-url", help="Override DATABASE_URL for this run."),
    ] = None,
) -> None:
    """Collect YouTube metadata for one small controlled search query."""

    runtime: CollectVideosRuntime | None = None
    try:
        settings = load_settings()
        if database_url is not None:
            settings = settings.model_copy(update={"database_url": database_url})

        ensure_database_current(settings.database_url)
        runtime = build_collect_videos_runtime(settings)
        result = runtime.use_case.execute(
            CollectVideosRequest(
                query_text=query,
                max_results=max_results,
                parameters=_search_parameters(
                    order=order,
                    published_after=published_after,
                    published_before=published_before,
                    region_code=region_code,
                ),
            )
        )
    except ConfigurationError as exc:
        _fail(f"Configuration error: {exc}", code=1)
    except PermanentYouTubeGatewayError as exc:
        _fail(f"YouTube request failed: {exc}", code=3)
    except MissingYouTubeMetadataError as exc:
        _fail(f"YouTube metadata was incomplete: {exc}", code=3)
    except TransientYouTubeGatewayError as exc:
        _fail(f"YouTube service temporarily unavailable: {exc}", code=4)
    except (MigrationError, RepositoryError) as exc:
        _fail(f"Database operation failed: {exc}", code=5)
    except Exception:
        _fail("Unexpected error: collection failed", code=6)
    finally:
        if runtime is not None:
            runtime.close()

    _print_result(result)


def _search_parameters(
    *,
    order: str | None,
    published_after: str | None,
    published_before: str | None,
    region_code: str | None,
) -> dict[str, str]:
    parameters: dict[str, str] = {}
    if order is not None:
        parameters["order"] = order
    if published_after is not None:
        parameters["publishedAfter"] = published_after
    if published_before is not None:
        parameters["publishedBefore"] = published_before
    if region_code is not None:
        parameters["regionCode"] = region_code
    return parameters


def _print_result(result: CollectVideosResult) -> None:
    typer.echo("Collection completed.")
    typer.echo(f"Query: {result.query_text}")
    typer.echo(f"Requested max results: {result.requested_max_results}")
    typer.echo(f"Search results returned: {result.search_result_count}")
    typer.echo(f"Unique videos: {result.unique_video_count}")
    typer.echo(f"Stored or updated videos: {result.stored_video_count}")
    typer.echo(f"Search hits recorded: {result.search_hit_count}")
    typer.echo(f"Duplicate search results skipped: {result.duplicate_search_result_count}")


def _fail(message: str, *, code: int) -> None:
    typer.secho(message, err=True, fg=typer.colors.RED)
    raise typer.Exit(code)
