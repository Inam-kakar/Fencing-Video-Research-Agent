"""Typer command-line interface for controlled metadata collection."""

from __future__ import annotations

from typing import Annotated

import typer

from fencing_video_research_agent.application import (
    CollectVideosRequest,
    CollectVideosResult,
    ListStoredVideosRequest,
    ListStoredVideosResult,
    MissingYouTubeMetadataError,
    ShowStoredVideoRequest,
    ShowStoredVideoResult,
    StoredVideoNotFoundError,
)
from fencing_video_research_agent.bootstrap import (
    CollectVideosRuntime,
    VideoInspectionRuntime,
    build_collect_videos_runtime,
    build_video_inspection_runtime,
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
MAX_VIDEO_LIST_RESULTS = 100
DESCRIPTION_PREVIEW_LENGTH = 500

app = typer.Typer(
    help="Collect and organize public fencing-video metadata.",
    no_args_is_help=True,
    invoke_without_command=False,
)
videos_app = typer.Typer(
    help="Inspect videos stored in the local research database.",
    no_args_is_help=True,
)
app.add_typer(videos_app, name="videos")


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


@videos_app.command("list")
def list_stored_videos(
    limit: Annotated[
        int,
        typer.Option(
            "--limit",
            min=1,
            max=MAX_VIDEO_LIST_RESULTS,
            help="Maximum stored videos to show.",
        ),
    ] = 20,
    database_url: Annotated[
        str | None,
        typer.Option("--database-url", help="Override DATABASE_URL for this read."),
    ] = None,
) -> None:
    """List videos already stored in the local database."""

    runtime: VideoInspectionRuntime | None = None
    try:
        settings = load_settings(require_youtube_api_key=False)
        if database_url is not None:
            settings = settings.model_copy(update={"database_url": database_url})

        ensure_database_current(settings.database_url)
        runtime = build_video_inspection_runtime(settings)
        result = runtime.list_videos.execute(ListStoredVideosRequest(limit=limit))
    except ConfigurationError as exc:
        _fail(f"Configuration error: {exc}", code=1)
    except (MigrationError, RepositoryError) as exc:
        _fail(f"Database operation failed: {exc}", code=5)
    except Exception:
        _fail("Unexpected error: video inspection failed", code=6)
    finally:
        if runtime is not None:
            runtime.close()

    _print_video_list(result)


@videos_app.command("show")
def show_stored_video(
    youtube_video_id: Annotated[str, typer.Argument(help="Stored YouTube video ID.")],
    database_url: Annotated[
        str | None,
        typer.Option("--database-url", help="Override DATABASE_URL for this read."),
    ] = None,
) -> None:
    """Show details for one video already stored in the local database."""

    runtime: VideoInspectionRuntime | None = None
    try:
        settings = load_settings(require_youtube_api_key=False)
        if database_url is not None:
            settings = settings.model_copy(update={"database_url": database_url})

        ensure_database_current(settings.database_url)
        runtime = build_video_inspection_runtime(settings)
        result = runtime.show_video.execute(
            ShowStoredVideoRequest(youtube_video_id=youtube_video_id),
        )
    except ConfigurationError as exc:
        _fail(f"Configuration error: {exc}", code=1)
    except StoredVideoNotFoundError as exc:
        _fail(f"Stored video not found: {exc.youtube_video_id}", code=3)
    except (MigrationError, RepositoryError) as exc:
        _fail(f"Database operation failed: {exc}", code=5)
    except Exception:
        _fail("Unexpected error: video inspection failed", code=6)
    finally:
        if runtime is not None:
            runtime.close()

    _print_video_detail(result)


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


def _print_video_list(result: ListStoredVideosResult) -> None:
    if not result.videos:
        typer.echo("No stored videos found.")
        return

    typer.echo("Stored videos:")
    for video in result.videos:
        typer.echo(
            " | ".join(
                (
                    video.youtube_video_id,
                    video.title,
                    video.channel_title,
                    f"Published: {_format_optional(video.published_at)}",
                    f"First seen: {_format_optional(video.first_seen_at)}",
                    f"Last refreshed: {_format_optional(video.last_refreshed_at)}",
                )
            )
        )


def _print_video_detail(result: ShowStoredVideoResult) -> None:
    video = result.video
    typer.echo(f"YouTube video ID: {video.youtube_video_id}")
    typer.echo(f"Title: {video.title}")
    typer.echo(f"Description: {_format_description(video.description)}")
    typer.echo(f"Channel ID: {video.channel_id}")
    typer.echo(f"Channel title: {video.channel_title}")
    typer.echo(f"Published: {_format_optional(video.published_at)}")
    typer.echo(f"Duration: {_format_duration(video.duration_seconds)}")
    typer.echo(f"View count: {_format_optional(video.view_count)}")
    typer.echo(f"Like count: {_format_optional(video.like_count)}")
    typer.echo(f"Comment count: {_format_optional(video.comment_count)}")
    typer.echo(f"Tags: {_format_tags(video.tags)}")
    typer.echo(f"Thumbnail URL: {_format_optional(video.thumbnail_url)}")
    typer.echo(f"Video URL: {_format_optional(video.video_url)}")
    typer.echo(f"First seen: {_format_optional(video.first_seen_at)}")
    typer.echo(f"Last refreshed: {_format_optional(video.last_refreshed_at)}")
    typer.echo(f"Annotation status: {_format_optional(video.annotation_status)}")


def _print_result(result: CollectVideosResult) -> None:
    typer.echo("Collection completed.")
    typer.echo(f"Query: {result.query_text}")
    typer.echo(f"Requested max results: {result.requested_max_results}")
    typer.echo(f"Search results returned: {result.search_result_count}")
    typer.echo(f"Unique videos: {result.unique_video_count}")
    typer.echo(f"Stored or updated videos: {result.stored_video_count}")
    typer.echo(f"Search hits recorded: {result.search_hit_count}")
    typer.echo(f"Duplicate search results skipped: {result.duplicate_search_result_count}")


def _format_optional(value: object | None) -> str:
    if value is None:
        return "not available"
    return str(value)


def _format_description(description: str | None) -> str:
    if description is None:
        return "not available"
    if len(description) <= DESCRIPTION_PREVIEW_LENGTH:
        return description
    return f"{description[: DESCRIPTION_PREVIEW_LENGTH - 3].rstrip()}..."


def _format_duration(duration_seconds: int | None) -> str:
    if duration_seconds is None:
        return "not available"
    hours, remainder = divmod(duration_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02}:{seconds:02}"
    return f"{minutes}:{seconds:02}"


def _format_tags(tags: tuple[str, ...]) -> str:
    if not tags:
        return "not available"
    return ", ".join(tags)


def _fail(message: str, *, code: int) -> None:
    typer.secho(message, err=True, fg=typer.colors.RED)
    raise typer.Exit(code)
