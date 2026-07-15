# ADR-0012: React Vite MUI frontend skeleton

## Status

Accepted

## Context

The project has a Python backend, SQLite persistence, command-line workflows, export
workflows, and a read-only FastAPI API. A professor-facing dashboard is a useful next
step, but the project does not yet need a full frontend with tables, forms, or
mutation workflows.

The selected frontend direction is React, TypeScript, Vite, and MUI. The frontend
must remain an outer interface and must not bypass the backend by reading SQLite,
backend `.env` files, or YouTube credentials.

## Decision

Create a small frontend skeleton under `frontend/`. It displays an app shell,
dashboard title, API health indicator, summary metric cards, and a note that larger
tables are postponed.

The frontend calls only:

- `GET /health`
- `GET /api/summary`

FastAPI receives minimal local-development CORS configuration for
`http://localhost:5173`, read-only `GET` requests, and no credentials.

## Alternatives considered

- Build the full dashboard immediately.
- Use Streamlit.
- Use Tailwind CSS or shadcn/ui for the first frontend.
- Let React read SQLite directly.
- Add annotation editing, export triggers, or collection UI now.

## Reasons for rejection

A full dashboard would mix skeleton setup with table, filtering, and interaction
decisions. Streamlit does not match the selected React direction and would create a
separate application model. Tailwind and shadcn/ui are flexible, but MUI provides a
more complete ready-made component system for dashboard cards, layout, chips, alerts,
and future forms. React must not read SQLite directly because the FastAPI API is the
public boundary for browser access. Write workflows need separate API, security, and
validation decisions.

## Consequences

The project gains a browser-visible dashboard foundation without changing the
database schema or backend write behavior. Future frontend milestones can add videos,
runs, and search-hit tables on top of the same API-client structure.

The trade-off is a new Node/Vite frontend toolchain and frontend dependency tree. The
initial UI is intentionally small and does not yet provide full dashboard navigation
or research review workflows.

## Performance impact

The skeleton makes two small read-only API calls at page load. No charts, table
libraries, caching, or complex state management are added.

## Security impact

The frontend does not receive `YOUTUBE_API_KEY`, does not read backend `.env` files,
does not call YouTube, and does not connect to SQLite. CORS is limited to the local
Vite development origin and `GET` methods without credentials.

## Migration and compatibility

No database migration is introduced. Existing CLI, export, collection, annotation,
and read-only API behavior remain compatible. The frontend build output and local
frontend environment files are ignored by Git, while source and lock files remain
tracked.

## Reversibility

The frontend directory, frontend documentation, CORS test, and small CORS middleware
configuration can be removed without altering the database or core backend
architecture.
