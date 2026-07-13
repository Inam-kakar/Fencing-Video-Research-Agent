# ADR-0005: CLI composition and controlled collection

## Status

Accepted

## Context

Earlier milestones established framework-free domain models, project-owned ports,
SQLAlchemy persistence with Alembic migrations, repository and Unit of Work
boundaries, an application collection use case, and an official YouTube Data API
adapter.

The project now needs a narrow user-facing entry point for running a small real
metadata collection into the local SQLite database while preserving the clean
architecture boundaries.

## Decision

Add a Typer command-line interface with one focused `collect` command. The CLI parses
arguments, loads settings, runs Alembic upgrade to `head`, builds the collection
workflow through a composition root, calls the application use case, and prints
concise result counts.

Add `bootstrap.py` as the composition root for wiring settings, the YouTube Data API
adapter, SQLAlchemy engine and session factory, SQLAlchemy Unit of Work, clock, and
`CollectVideosUseCase`.

The CLI remains thin. It does not construct raw SQLAlchemy sessions, call Google APIs
directly, parse raw Google response dictionaries, or contain business rules.

## Alembic Before Collection

The CLI runs Alembic upgrade to `head` before collection so the local SQLite database
is ready without using `Base.metadata.create_all()` as a schema path. The migration
helper overrides `sqlalchemy.url` at runtime, so environment and CLI database URL
settings are respected.

## Real API Usage

The first CLI caps `--max-results` at `50` and defaults to `5`. This keeps early real
collection controlled and quota-aware while still allowing a useful smoke test.

Normal automated tests remain offline and deterministic. Real YouTube API validation
is documented as a manual smoke test only.

## Security

The API key is loaded through settings and used only to construct the official Google
client. The CLI prints sanitized messages and must not print the API key, `.env`
contents, raw Google API responses, credential-bearing URLs, or raw stack traces.

## Trade-offs

Running migrations automatically is convenient for a SQLite-first research workflow,
but it means the CLI can change local database files before collection starts. This is
acceptable for the initial local-only tool because schema changes are Alembic-managed
and no destructive migration is introduced in this milestone.

The first CLI exposes only a small set of search options. This limits flexibility but
keeps the public command understandable and reproducible.

## Not Implemented Yet

This milestone does not add exports, pandas export logic, video downloading, computer
vision, event or scoring detection, web UI, cloud deployment, schema changes, live
automated YouTube tests, failed-run persistence, or broad documentation cleanup.

## Migration And Compatibility

No database schema migration is added. Existing domain, application, port,
repository, and YouTube adapter contracts remain compatible.

## Reversibility

Before users depend on the CLI, this change can be reversed by removing the interface
package, bootstrap module, migration helper, console script entry point, and related
tests/docs. Existing domain, application, persistence, and adapter code can remain in
place.
