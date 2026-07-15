# ADR-0011: Read-only FastAPI API

## Status

Accepted

## Context

The project already has a CLI, SQLite persistence, Alembic migrations, read models,
manual annotation workflows, and CSV/JSON exports. A future professor-facing dashboard
needs HTTP/JSON access to stored local research data, but the React frontend has not
been implemented yet.

The API must respect the existing clean architecture rules. Domain and application
code must not depend on FastAPI, SQLAlchemy, Google API clients, environment-variable
details, or raw Google response dictionaries.

## Decision

Add a small FastAPI app factory as an outer interface layer. The API exposes read-only
endpoints for health checks, dashboard summary counts, stored videos, collection runs,
and search-hit provenance rows.

The API uses the existing application/read-use-case boundary and SQLAlchemy read
repositories through bootstrap wiring. It runs Alembic upgrade to head once during app
creation, then serves bounded read-only endpoints. It loads settings with
`require_youtube_api_key=False` and does not instantiate the YouTube client.

## Alternatives considered

- Build the React dashboard first.
- Let React read SQLite directly.
- Add write endpoints for collection, export, or annotation editing now.
- Add CORS in the API milestone.
- Use Typer output as the dashboard data source.

## Reasons for rejection

React should depend on a stable backend contract, so the API comes first. Browser code
must not talk directly to SQLite because that would bypass the application boundary and
make future deployment harder. Write endpoints would expand the milestone into
workflow, validation, and security decisions that are not needed for the first
dashboard foundation. CORS is deferred until a frontend origin actually exists. CLI
output is for humans, not a durable machine API contract.

## Consequences

The project gains a professional HTTP/JSON backend foundation while preserving the
existing CLI and export workflows. The API remains intentionally limited and easy to
test offline. Future frontend work can consume stable JSON response schemas instead of
coupling to the database or CLI text output.

The trade-off is one additional production dependency group for FastAPI and Uvicorn,
plus httpx for API tests. The API does not yet support frontend-origin CORS, write
workflows, authentication, or deployment concerns.

## Performance impact

Endpoints use bounded `limit` and `offset` parameters. Read projections are shaped for
dashboard tables and avoid returning ORM objects. The initial implementation is
appropriate for local SQLite-backed research datasets. Larger datasets may later need
more targeted indexes, richer filters, or cursor-style pagination.

## Security impact

The API does not require `YOUTUBE_API_KEY`, does not call YouTube, and does not create
the Google API client. It returns project-owned response schemas and safe 404 messages.
It does not expose raw SQL, raw Google responses, stack traces, `.env` contents, or API
keys.

## Migration and compatibility

No database schema changes are introduced. No Alembic revision is added. Existing CLI,
collection, annotation, and export commands remain compatible. React, MUI, CORS, write
endpoints, authentication, Docker, and deployment are out of scope for this decision.

## Reversibility

The API package, FastAPI/Uvicorn/httpx dependencies, and API-specific read projections
can be removed without changing the database schema. Existing CLI and persistence
behavior would remain intact.
