# ADR-0013: React MUI read-only browsing tables

## Status

Accepted

## Context

Milestone 11C introduced a React, TypeScript, Vite, and MUI frontend skeleton that
proved the browser can call the read-only FastAPI API. The frontend displayed API
health and summary metric cards, but it did not yet let a researcher browse the
stored videos, collection runs, or search-hit provenance records that already exist
in the backend API.

## Decision

Add read-only frontend views for stored videos, collection runs, and search-hit
provenance. Use MUI `Tabs` with simple React state for navigation, and MUI `Table`
components for bounded browsing tables.

The frontend continues to call FastAPI only. It uses explicit typed API client
functions for:

- `GET /api/videos`
- `GET /api/runs`
- `GET /api/search-hits`

## Alternatives considered

- Add React Router.
- Add MUI DataGrid.
- Add annotation editing, export triggers, or YouTube collection UI.
- Add new backend table endpoints or write routes.

## Reasons for rejection

React Router is unnecessary while the app has four simple top-level views and does
not need deep links. MUI DataGrid would add another dependency and a larger API
surface before the project needs advanced grid behavior. Annotation editing, export
triggers, and collection UI require write workflows and security decisions that are
outside this read-only milestone. Existing FastAPI responses already provide the
fields needed for the first browsing tables.

## Consequences

The frontend becomes useful for browsing the existing research database while
remaining read-only and dependency-light. Future milestones can add richer detail
views, table sorting, server-side totals, or write workflows after explicit API
decisions.

The trade-off is that pagination remains intentionally simple. The current API
returns the current page count rather than a full total count, so the UI does not
pretend to know the full database size.

## Performance impact

Each table loads a bounded page of up to 50 records. This is appropriate for the
current local research workflow. Larger datasets may later need total counts, cursor
pagination, or more specific filters.

## Security impact

The frontend does not receive `YOUTUBE_API_KEY`, does not call YouTube, does not read
backend `.env` files, and does not connect to SQLite. It exposes no annotation
editing controls, export buttons, collection UI, or backend write behavior.

## Migration and compatibility

No database migration or backend API change is introduced. Existing CLI, export,
collection, annotation, and read-only API behavior remain compatible.

## Reversibility

The table pages and navigation can be removed from the frontend without affecting the
backend, database schema, or existing CLI workflows.
