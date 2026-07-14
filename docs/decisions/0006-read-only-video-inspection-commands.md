# ADR-0006: Read-only video inspection commands

## Status

Accepted

## Context

Earlier milestones added metadata collection through the official YouTube Data API,
SQLAlchemy persistence, Alembic migrations, repository and Unit of Work boundaries,
and a Typer `collect` command. A manual smoke test confirmed that collection can store
videos in the local SQLite database.

The next small user workflow is inspecting videos already stored locally. This should
not spend YouTube API quota, require an API key, or mix SQLAlchemy query details into
the CLI or application layer.

## Decision

Add a `videos` Typer command group with:

- `videos list`
- `videos show <youtube_video_id>`

The commands load database and logging settings without requiring `YOUTUBE_API_KEY`,
run Alembic upgrade to `head`, build read-only application use cases through the
composition root, and print stored video summaries or details.

Read/query DTOs and a `StoredDataReader` port are added for inspection. A SQLAlchemy
reader implementation lives in infrastructure and performs the concrete joins and
ordering against the existing schema.

## Reasons

Stored-video inspection is a real Phase 1 workflow: it lets the researcher verify what
has already been collected before later review and export features exist.

The commands do not require `YOUTUBE_API_KEY` because they read only local SQLite
data. Requiring a YouTube key for a local read would make the research database less
inspectable and would confuse configuration errors with database state.

The commands do not call YouTube because inspection must be read-only, deterministic,
and quota-free. Metadata refresh remains a separate future workflow.

## Read Boundary

Read/query repositories are separate from write repositories because inspection needs
projection-shaped data rather than domain objects prepared for writes. Keeping this
reader behind a port avoids exposing SQLAlchemy sessions, ORM records, or raw SQL to
application use cases.

The CLI remains thin: it parses options, runs migrations, calls use cases, displays
results, and selects exit codes. It does not contain raw SQL, database session
construction, YouTube client construction, or business rules.

## Trade-offs

The first read commands print plain text instead of adding a table-rendering
dependency. This keeps the milestone dependency-free and easy to test, but the output
is intentionally modest.

The read side introduces projection DTOs in addition to existing domain models. This
is a pragmatic split: inspection output needs display-oriented fields such as
annotation status and stored timestamps, while domain models remain focused on
research concepts and write workflows.

## Postponed Work

Collection-run inspection commands are postponed to Milestone 6B so this milestone can
stay focused on stored videos only.

This milestone does not add exports, pandas logic, annotation editing, video
downloading, computer vision, event or scoring detection, web UI, cloud deployment,
schema changes, Alembic migrations, new YouTube API calls, or new dependencies.

## Security Impact

Read-only commands do not require, print, log, or expose the YouTube API key. They
also avoid raw Google responses entirely because they do not call the YouTube adapter.

## Migration And Compatibility

No database schema migration is added. The commands use the existing Phase 1 schema
and run Alembic upgrade to `head` before reading so a local SQLite database is ready
for inspection.

Existing `collect` behavior remains unchanged and still requires `YOUTUBE_API_KEY`.

## Reversibility

This decision can be reversed by removing the `videos` CLI group, read use cases,
stored-data reader port, SQLAlchemy read repository, and related tests/docs. No stored
data migration is required because no schema change is introduced.
