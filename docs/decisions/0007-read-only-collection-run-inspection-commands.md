# ADR-0007: Read-only collection-run inspection commands

## Status

Accepted

## Context

Earlier milestones added reproducible metadata collection, SQLite persistence with
Alembic migrations, a Typer `collect` command, and read-only stored-video inspection.
The database already records search queries, collection runs, search hits, videos, and
latest YouTube metadata.

Researchers now need to inspect previous collection runs so they can understand when a
query was executed, which parameters were used, and which videos were returned.

## Decision

Add a `runs` Typer command group with:

- `runs list`
- `runs show <run_id>`

The commands load settings without requiring `YOUTUBE_API_KEY`, run Alembic upgrade to
`head`, build read-only application use cases through the composition root, and read
only from the local database.

Milestone 6B extends the existing `StoredDataReader` read boundary from Milestone 6A
with collection-run DTOs and reader methods. The SQLAlchemy implementation remains in
the infrastructure layer.

## Reproducibility

Collection-run inspection supports reproducible research by making the provenance of
stored videos visible: the query text, query parameters, run timing, run status, hit
count, and videos returned by a run can be inspected after collection.

## API Key And YouTube Access

The commands do not require `YOUTUBE_API_KEY` because they inspect only local SQLite
data. They do not instantiate the YouTube client and do not call the YouTube Data API.
This keeps inspection quota-free, deterministic, and usable even when credentials are
not configured.

## Schema And Migration

No schema migration is needed. The existing schema already stores the required
relationship path:

```text
search_queries -> collection_runs -> search_hits -> videos
```

The commands still run Alembic upgrade to `head` before reading so a missing local
SQLite database is initialized through the normal migration path.

## Trade-offs

The output remains plain text rather than using a table-rendering dependency. This
keeps the milestone small and dependency-free, but formatting is intentionally modest.

The commands do not print stored collection-run error messages. Error-message display
can be reconsidered later with explicit sanitization requirements.

## Postponed Work

This milestone does not add exports, pandas logic, annotation editing, metadata
refresh, new YouTube API calls, video downloading, computer vision, event or scoring
detection, web UI, cloud deployment, schema changes, Alembic migrations, or new
dependencies.

## Security Impact

The commands must not print API keys, `.env` contents, raw Google responses, raw SQL,
stack traces, credential-bearing URLs, or unsanitized internal errors.

## Migration And Compatibility

No persistent schema changes are introduced. Existing collection and video inspection
commands remain compatible.

## Reversibility

This decision can be reversed by removing the `runs` CLI group, collection-run read
DTOs and use cases, SQLAlchemy run reader methods, tests, and documentation. No data
migration is required because the database schema is unchanged.
