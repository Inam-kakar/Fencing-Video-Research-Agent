"""Typer command-line interface for controlled metadata collection."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Annotated

import typer

from fencing_video_research_agent.application import (
    AnnotationVideoNotFoundError,
    AnnotationWriteResult,
    ClearAnnotationLabelRequest,
    ClearAnnotationLabelResult,
    CollectVideosRequest,
    CollectVideosResult,
    ExportVideosRequest,
    ExportVideosResult,
    InvalidExportFormatError,
    InvalidReviewStatusError,
    ListCollectionRunsRequest,
    ListCollectionRunsResult,
    ListStoredVideosRequest,
    ListStoredVideosResult,
    MissingYouTubeMetadataError,
    SetAnnotationLabelRequest,
    SetAnnotationNotesRequest,
    SetAnnotationReviewStatusRequest,
    ShowAnnotationRequest,
    ShowAnnotationResult,
    ShowCollectionRunRequest,
    ShowCollectionRunResult,
    ShowStoredVideoRequest,
    ShowStoredVideoResult,
    StoredCollectionRunNotFoundError,
    StoredVideoNotFoundError,
)
from fencing_video_research_agent.bootstrap import (
    AnnotationRuntime,
    CollectVideosRuntime,
    ExportVideosRuntime,
    VideoInspectionRuntime,
    build_annotation_runtime,
    build_collect_videos_runtime,
    build_export_videos_runtime,
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
    ExportFileExistsError,
    PermanentYouTubeGatewayError,
    RepositoryError,
    TransientYouTubeGatewayError,
)

MAX_COLLECT_RESULTS = 50
MAX_VIDEO_LIST_RESULTS = 100
MAX_RUN_LIST_RESULTS = 100
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
runs_app = typer.Typer(
    help="Inspect collection runs stored in the local research database.",
    no_args_is_help=True,
)
annotations_app = typer.Typer(
    help="Review stored videos and edit researcher annotations.",
    no_args_is_help=True,
)
export_app = typer.Typer(
    help="Export local research data to analysis-friendly files.",
    no_args_is_help=True,
)
app.add_typer(videos_app, name="videos")
app.add_typer(runs_app, name="runs")
app.add_typer(annotations_app, name="annotations")
app.add_typer(export_app, name="export")


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


@annotations_app.command("show")
def show_annotation(
    youtube_video_id: Annotated[str, typer.Argument(help="Stored YouTube video ID.")],
    database_url: Annotated[
        str | None,
        typer.Option("--database-url", help="Override DATABASE_URL for this annotation read."),
    ] = None,
) -> None:
    """Show manual researcher annotation fields for a stored video."""

    runtime: AnnotationRuntime | None = None
    try:
        settings = load_settings(require_youtube_api_key=False)
        if database_url is not None:
            settings = settings.model_copy(update={"database_url": database_url})

        ensure_database_current(settings.database_url)
        runtime = build_annotation_runtime(settings)
        result = runtime.show_annotation.execute(
            ShowAnnotationRequest(youtube_video_id=youtube_video_id),
        )
    except ConfigurationError as exc:
        _fail(f"Configuration error: {exc}", code=1)
    except AnnotationVideoNotFoundError as exc:
        _fail(f"Stored video not found: {exc.youtube_video_id}", code=3)
    except ValueError as exc:
        _fail(f"Invalid annotation input: {exc}", code=2)
    except (MigrationError, RepositoryError) as exc:
        _fail(f"Database operation failed: {exc}", code=5)
    except Exception:
        _fail("Unexpected error: annotation inspection failed", code=6)
    finally:
        if runtime is not None:
            runtime.close()

    _print_annotation_detail(result)


@annotations_app.command("set-status")
def set_annotation_status(
    youtube_video_id: Annotated[str, typer.Argument(help="Stored YouTube video ID.")],
    status: Annotated[str, typer.Argument(help="Review status: unreviewed or reviewed.")],
    database_url: Annotated[
        str | None,
        typer.Option("--database-url", help="Override DATABASE_URL for this annotation write."),
    ] = None,
) -> None:
    """Set a stored video's manual review status."""

    runtime: AnnotationRuntime | None = None
    try:
        settings = load_settings(require_youtube_api_key=False)
        if database_url is not None:
            settings = settings.model_copy(update={"database_url": database_url})

        ensure_database_current(settings.database_url)
        runtime = build_annotation_runtime(settings)
        result = runtime.set_review_status.execute(
            SetAnnotationReviewStatusRequest(
                youtube_video_id=youtube_video_id,
                status=status,
            ),
        )
    except ConfigurationError as exc:
        _fail(f"Configuration error: {exc}", code=1)
    except AnnotationVideoNotFoundError as exc:
        _fail(f"Stored video not found: {exc.youtube_video_id}", code=3)
    except InvalidReviewStatusError as exc:
        _fail(str(exc), code=2)
    except ValueError as exc:
        _fail(f"Invalid annotation input: {exc}", code=2)
    except (MigrationError, RepositoryError) as exc:
        _fail(f"Database operation failed: {exc}", code=5)
    except Exception:
        _fail("Unexpected error: annotation update failed", code=6)
    finally:
        if runtime is not None:
            runtime.close()

    _print_annotation_status_update(result)


@annotations_app.command("set-notes")
def set_annotation_notes(
    youtube_video_id: Annotated[str, typer.Argument(help="Stored YouTube video ID.")],
    notes: Annotated[str, typer.Option("--notes", help="Researcher notes to store.")],
    database_url: Annotated[
        str | None,
        typer.Option("--database-url", help="Override DATABASE_URL for this annotation write."),
    ] = None,
) -> None:
    """Set manual notes for a stored video."""

    runtime: AnnotationRuntime | None = None
    try:
        settings = load_settings(require_youtube_api_key=False)
        if database_url is not None:
            settings = settings.model_copy(update={"database_url": database_url})

        ensure_database_current(settings.database_url)
        runtime = build_annotation_runtime(settings)
        result = runtime.set_notes.execute(
            SetAnnotationNotesRequest(youtube_video_id=youtube_video_id, notes=notes),
        )
    except ConfigurationError as exc:
        _fail(f"Configuration error: {exc}", code=1)
    except AnnotationVideoNotFoundError as exc:
        _fail(f"Stored video not found: {exc.youtube_video_id}", code=3)
    except ValueError as exc:
        _fail(f"Invalid annotation input: {exc}", code=2)
    except (MigrationError, RepositoryError) as exc:
        _fail(f"Database operation failed: {exc}", code=5)
    except Exception:
        _fail("Unexpected error: annotation update failed", code=6)
    finally:
        if runtime is not None:
            runtime.close()

    _print_annotation_notes_update(result)


@annotations_app.command("set-label")
def set_annotation_label(
    youtube_video_id: Annotated[str, typer.Argument(help="Stored YouTube video ID.")],
    label: Annotated[str, typer.Argument(help="Single relevance label to store.")],
    database_url: Annotated[
        str | None,
        typer.Option("--database-url", help="Override DATABASE_URL for this annotation write."),
    ] = None,
) -> None:
    """Set the single relevance label for a stored video."""

    runtime: AnnotationRuntime | None = None
    try:
        settings = load_settings(require_youtube_api_key=False)
        if database_url is not None:
            settings = settings.model_copy(update={"database_url": database_url})

        ensure_database_current(settings.database_url)
        runtime = build_annotation_runtime(settings)
        result = runtime.set_label.execute(
            SetAnnotationLabelRequest(youtube_video_id=youtube_video_id, label=label),
        )
    except ConfigurationError as exc:
        _fail(f"Configuration error: {exc}", code=1)
    except AnnotationVideoNotFoundError as exc:
        _fail(f"Stored video not found: {exc.youtube_video_id}", code=3)
    except ValueError as exc:
        _fail(f"Invalid annotation input: {exc}", code=2)
    except (MigrationError, RepositoryError) as exc:
        _fail(f"Database operation failed: {exc}", code=5)
    except Exception:
        _fail("Unexpected error: annotation update failed", code=6)
    finally:
        if runtime is not None:
            runtime.close()

    _print_annotation_label_update(result)


@annotations_app.command("clear-label")
def clear_annotation_label(
    youtube_video_id: Annotated[str, typer.Argument(help="Stored YouTube video ID.")],
    database_url: Annotated[
        str | None,
        typer.Option("--database-url", help="Override DATABASE_URL for this annotation write."),
    ] = None,
) -> None:
    """Clear the single relevance label for a stored video."""

    runtime: AnnotationRuntime | None = None
    try:
        settings = load_settings(require_youtube_api_key=False)
        if database_url is not None:
            settings = settings.model_copy(update={"database_url": database_url})

        ensure_database_current(settings.database_url)
        runtime = build_annotation_runtime(settings)
        result = runtime.clear_label.execute(
            ClearAnnotationLabelRequest(youtube_video_id=youtube_video_id),
        )
    except ConfigurationError as exc:
        _fail(f"Configuration error: {exc}", code=1)
    except AnnotationVideoNotFoundError as exc:
        _fail(f"Stored video not found: {exc.youtube_video_id}", code=3)
    except ValueError as exc:
        _fail(f"Invalid annotation input: {exc}", code=2)
    except (MigrationError, RepositoryError) as exc:
        _fail(f"Database operation failed: {exc}", code=5)
    except Exception:
        _fail("Unexpected error: annotation update failed", code=6)
    finally:
        if runtime is not None:
            runtime.close()

    _print_annotation_label_clear(result)


@export_app.command("videos")
def export_videos(
    export_format: Annotated[
        str,
        typer.Option(
            "--format",
            help="Export format: csv or json.",
        ),
    ] = "csv",
    output: Annotated[
        Path | None,
        typer.Option("--output", help="Output file path. Defaults to data/exports/videos.*."),
    ] = None,
    overwrite: Annotated[
        bool,
        typer.Option("--overwrite", help="Overwrite the output file if it already exists."),
    ] = False,
    database_url: Annotated[
        str | None,
        typer.Option("--database-url", help="Override DATABASE_URL for this export."),
    ] = None,
) -> None:
    """Export stored video metadata, annotations, and compact provenance."""

    runtime: ExportVideosRuntime | None = None
    try:
        settings = load_settings(require_youtube_api_key=False)
        if database_url is not None:
            settings = settings.model_copy(update={"database_url": database_url})

        ensure_database_current(settings.database_url)
        runtime = build_export_videos_runtime(settings)
        result = runtime.use_case.execute(
            ExportVideosRequest(
                export_format=export_format,
                output_path=output,
                overwrite=overwrite,
            ),
        )
    except ConfigurationError as exc:
        _fail(f"Configuration error: {exc}", code=1)
    except InvalidExportFormatError as exc:
        _fail(str(exc), code=2)
    except ExportFileExistsError as exc:
        _fail(
            f"Export file already exists: {_format_path(exc.output_path)}. "
            "Use --overwrite to replace it.",
            code=3,
        )
    except (MigrationError, RepositoryError) as exc:
        _fail(f"Database operation failed: {exc}", code=5)
    except Exception:
        _fail("Unexpected error: export failed", code=6)
    finally:
        if runtime is not None:
            runtime.close()

    _print_export_videos_result(result)


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


@runs_app.command("list")
def list_collection_runs(
    limit: Annotated[
        int,
        typer.Option(
            "--limit",
            min=1,
            max=MAX_RUN_LIST_RESULTS,
            help="Maximum collection runs to show.",
        ),
    ] = 20,
    database_url: Annotated[
        str | None,
        typer.Option("--database-url", help="Override DATABASE_URL for this read."),
    ] = None,
) -> None:
    """List collection runs already stored in the local database."""

    runtime: VideoInspectionRuntime | None = None
    try:
        settings = load_settings(require_youtube_api_key=False)
        if database_url is not None:
            settings = settings.model_copy(update={"database_url": database_url})

        ensure_database_current(settings.database_url)
        runtime = build_video_inspection_runtime(settings)
        result = runtime.list_collection_runs.execute(ListCollectionRunsRequest(limit=limit))
    except ConfigurationError as exc:
        _fail(f"Configuration error: {exc}", code=1)
    except (MigrationError, RepositoryError) as exc:
        _fail(f"Database operation failed: {exc}", code=5)
    except Exception:
        _fail("Unexpected error: collection-run inspection failed", code=6)
    finally:
        if runtime is not None:
            runtime.close()

    _print_collection_run_list(result)


@runs_app.command("show")
def show_collection_run(
    run_id: Annotated[int, typer.Argument(min=1, help="Stored collection run ID.")],
    database_url: Annotated[
        str | None,
        typer.Option("--database-url", help="Override DATABASE_URL for this read."),
    ] = None,
) -> None:
    """Show details for one collection run already stored in the local database."""

    runtime: VideoInspectionRuntime | None = None
    try:
        settings = load_settings(require_youtube_api_key=False)
        if database_url is not None:
            settings = settings.model_copy(update={"database_url": database_url})

        ensure_database_current(settings.database_url)
        runtime = build_video_inspection_runtime(settings)
        result = runtime.show_collection_run.execute(ShowCollectionRunRequest(run_id=run_id))
    except ConfigurationError as exc:
        _fail(f"Configuration error: {exc}", code=1)
    except StoredCollectionRunNotFoundError as exc:
        _fail(f"Collection run not found: {exc.run_id}", code=3)
    except (MigrationError, RepositoryError) as exc:
        _fail(f"Database operation failed: {exc}", code=5)
    except Exception:
        _fail("Unexpected error: collection-run inspection failed", code=6)
    finally:
        if runtime is not None:
            runtime.close()

    _print_collection_run_detail(result)


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


def _print_annotation_detail(result: ShowAnnotationResult) -> None:
    typer.echo(f"YouTube video ID: {result.youtube_video_id}")
    annotation = result.annotation
    if annotation is None:
        typer.echo("No annotation recorded yet.")
        return

    typer.echo(f"Review status: {annotation.review_status.value}")
    typer.echo(f"Notes: {_format_optional(annotation.notes)}")
    typer.echo(f"Relevance label: {_format_optional(annotation.relevance_label)}")
    typer.echo(f"Competition name: {_format_optional(annotation.competition_name)}")
    typer.echo(f"Fencer names: {_format_tags(annotation.fencer_names)}")
    typer.echo(f"Weapon category: {_format_optional(annotation.weapon_category)}")
    typer.echo(f"Event notes: {_format_optional(annotation.event_notes)}")
    typer.echo(f"Updated at: {annotation.updated_at}")


def _print_annotation_status_update(result: AnnotationWriteResult) -> None:
    typer.echo("Annotation review status updated.")
    typer.echo(f"YouTube video ID: {result.annotation.youtube_video_id}")
    typer.echo(f"Review status: {result.annotation.review_status.value}")


def _print_annotation_notes_update(result: AnnotationWriteResult) -> None:
    typer.echo("Annotation notes updated.")
    typer.echo(f"YouTube video ID: {result.annotation.youtube_video_id}")


def _print_annotation_label_update(result: AnnotationWriteResult) -> None:
    typer.echo("Annotation relevance label updated.")
    typer.echo(f"YouTube video ID: {result.annotation.youtube_video_id}")
    typer.echo(f"Relevance label: {_format_optional(result.annotation.relevance_label)}")


def _print_annotation_label_clear(result: ClearAnnotationLabelResult) -> None:
    if result.changed:
        typer.echo("Annotation relevance label cleared.")
    elif result.annotation is None:
        typer.echo("No annotation recorded yet; relevance label is already clear.")
    else:
        typer.echo("Annotation relevance label was already clear.")
    typer.echo(f"YouTube video ID: {result.youtube_video_id}")


def _print_export_videos_result(result: ExportVideosResult) -> None:
    typer.echo(f"Export path: {_format_path(result.output_path)}")
    typer.echo(f"Row count: {result.row_count}")
    typer.echo(f"Format: {result.export_format}")


def _print_collection_run_list(result: ListCollectionRunsResult) -> None:
    if not result.runs:
        typer.echo("No collection runs found.")
        return

    typer.echo("Collection runs:")
    for run in result.runs:
        typer.echo(
            " | ".join(
                (
                    f"Run ID: {int(run.run_id)}",
                    f"Query: {run.query_text}",
                    f"Status: {run.status}",
                    f"Started: {_format_optional(run.started_at)}",
                    f"Completed: {_format_optional(run.completed_at)}",
                    f"Hits: {run.hit_count}",
                )
            )
        )


def _print_collection_run_detail(result: ShowCollectionRunResult) -> None:
    run = result.run
    typer.echo(f"Run ID: {int(run.run_id)}")
    typer.echo(f"Query: {run.query_text}")
    typer.echo(f"Query parameters: {_format_parameters(run.query_parameters)}")
    typer.echo(f"Status: {run.status}")
    typer.echo(f"Started: {_format_optional(run.started_at)}")
    typer.echo(f"Completed: {_format_optional(run.completed_at)}")
    typer.echo(f"Hit count: {run.hit_count}")
    if not run.hits:
        typer.echo("Returned videos: none")
        return

    typer.echo("Returned videos:")
    for hit in run.hits:
        typer.echo("")
        typer.echo(f"Rank: {_format_optional(hit.rank)}")
        typer.echo(f"  YouTube video ID: {hit.youtube_video_id}")
        typer.echo(f"  Title: {hit.title}")
        typer.echo(f"  Channel: {hit.channel_title}")


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


def _format_parameters(parameters: Mapping[str, object]) -> str:
    items = sorted(parameters.items())
    if not items:
        return "not available"
    return ", ".join(f"{key}={value}" for key, value in items)


def _format_path(path: Path) -> str:
    return path.as_posix()


def _fail(message: str, *, code: int) -> None:
    typer.secho(message, err=True, fg=typer.colors.RED)
    raise typer.Exit(code)
