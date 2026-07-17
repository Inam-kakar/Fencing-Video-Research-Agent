# ADR-0015: Browser metadata collection

## Status

Accepted

## Context

The project already supports official YouTube metadata collection through the CLI,
preserves search/query provenance in SQLite, exposes stored data through FastAPI, and
provides a React/MUI dashboard for browsing and annotating stored videos.

After browsing and annotation, the next Phase 1 workflow gap is local search
bootstrapping. A researcher may search the browser dashboard for an opponent or topic
that has no local records yet. The browser needs a controlled way to ask the backend
to collect metadata, while preserving the existing clean architecture and secret
handling rules.

## Decision

Add one local API endpoint:

```text
POST /api/collection-runs
```

The request accepts only:

- `query`
- `max_results`

The backend validates the request, caps browser-triggered `max_results` at 25, and
calls the existing `CollectVideosUseCase`. The use case continues to use the official
YouTube Data API adapter, the YouTube gateway port, SQLAlchemy repositories, and the
Unit of Work transaction boundary.

The React/MUI frontend adds a controlled collection panel on the Videos tab. It sends
only the query and max-results values to FastAPI, then refreshes the local stored
videos after a successful collection.

## Alternatives considered

- Keep collection as a CLI-only workflow.
- Let React call YouTube directly.
- Let React receive `YOUTUBE_API_KEY`.
- Add arbitrary YouTube API parameter editing in the browser.
- Add background jobs or a scheduler.
- Add video downloading or video-analysis workflows.

## Reasons for rejection

Keeping collection CLI-only leaves the browser unable to recover when local search has
no results. React must not call YouTube directly or receive the API key because
secrets belong in backend settings only. Arbitrary YouTube parameters would expand the
browser contract before the basic collection workflow is proven. Background jobs and
schedulers are unnecessary for the small, controlled Phase 1 local workflow. Video
downloading and analysis are Phase 2 or later research directions and remain out of
scope.

## Consequences

The dashboard can now support a complete Phase 1 loop:

```text
collect -> browse -> annotate -> inspect provenance -> export
```

The API is no longer limited to reads plus annotation editing; it now has one
backend-only YouTube collection write path. The route must therefore keep validation,
CORS, and error messages narrow and explicit.

## Performance impact

Browser collection is synchronous and capped at 25 requested results. This is
appropriate for local professor-facing demos and small Phase 1 metadata collection.
Larger collection protocols may later need separate planning for batching, progress
reporting, retries, or background execution.

## Security impact

`YOUTUBE_API_KEY` remains backend-only. The frontend sends only `query` and
`max_results`, never reads `.env`, never connects to SQLite, and never calls YouTube
directly. The backend returns sanitized errors and does not expose raw Google
responses, API keys, stack traces, or database internals.

Local-development CORS allows `GET`, `PATCH`, and `POST` from
`http://localhost:5173` with JSON content type and no credentials.

## Migration and compatibility

No database schema change is introduced. The endpoint writes through the existing
collection use case and therefore preserves the existing provenance relationship:

```text
search_queries -> collection_runs -> search_hits -> videos
```

Existing CLI collection, inspection, annotation, and export workflows remain
compatible. Existing CSV/JSON exports continue to read from the same tables.

## Reversibility

The POST route, frontend collection panel, CORS method addition, and documentation can
be removed without changing the database schema. The CLI collection workflow would
continue to work.
