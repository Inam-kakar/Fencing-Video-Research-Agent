# ADR-0014: Browser annotation editing

## Status

Accepted

## Context

The project already supports manual video annotation through the CLI and application
layer. Milestone 11D added a React, TypeScript, Vite, and MUI frontend for browsing
stored videos, collection runs, and search-hit provenance through FastAPI.

The next useful browser workflow is a small write path for researcher review. This is
still Phase 1 because it edits local metadata-review fields for already collected
videos. It does not introduce video downloading, computer vision, event detection,
model training, deployment, or production authentication.

## Decision

Add one FastAPI endpoint:

```text
PATCH /api/videos/{youtube_video_id}/annotation
```

The endpoint updates only:

- `review_status`
- `relevance_label`
- `notes`

It returns an updated annotation summary and does not call YouTube or require
`YOUTUBE_API_KEY`. A combined application-layer update use case performs the write in
one Unit of Work transaction so multiple edited fields cannot partially commit.

The React/MUI frontend adds an edit dialog from the Videos tab only. The dialog loads
the current video detail, lets the researcher edit the approved fields, saves through
the PATCH endpoint, and refreshes the videos table.

Local-development CORS now allows `GET` and `PATCH` from
`http://localhost:5173`, with JSON content-type headers and no credentials.

## Alternatives considered

- Keep browser annotation editing postponed.
- Call existing field-specific annotation use cases sequentially from the route.
- Allow editing richer annotation fields.
- Add editing from collection-run or search-hit tables.
- Add export, collection, or YouTube metadata editing UI.
- Add authentication or reviewer identity now.

## Reasons for rejection

Postponing browser editing would leave the dashboard read-only despite the existing
annotation use cases. Sequential field-specific use cases could commit one field
before another fails, which is not appropriate for a single browser save action.
Richer annotation fields need a clearer research protocol before becoming browser
editable. Editing from runs or search-hit tables would expand the interaction model
before the Videos tab workflow is proven. Export and collection UI are separate
workflows with different validation and safety concerns. Authentication and reviewer
identity are out of Phase 1 local-demo scope.

## Consequences

The browser becomes useful for the core manual review loop while preserving clean
architecture boundaries. FastAPI routes remain thin, SQLAlchemy stays in
infrastructure, and the application layer remains independent of FastAPI and browser
details.

The trade-off is that the API is no longer entirely read-only. Documentation and CORS
must describe the single permitted write path precisely.

## Performance impact

The dialog loads one video detail before editing and sends one PATCH request when the
researcher saves. The videos table then reloads its bounded page. This is appropriate
for local SQLite-backed review workflows.

## Security impact

The endpoint does not use or expose YouTube credentials, raw Google responses, raw
SQL, stack traces, or `.env` contents. CORS remains limited to the local Vite
development origin and does not allow credentials. The frontend still calls FastAPI
only and does not access SQLite directly.

## Migration and compatibility

No database migration is introduced. Existing CLI annotation commands, read-only
table endpoints, export commands, and collection workflows remain compatible. The new
endpoint creates or updates rows in the existing `research_annotations` table for
stored videos only.

## Reversibility

The PATCH route, combined application use case, frontend dialog, CORS method addition,
and documentation can be removed without changing the database schema. Existing CLI
annotation workflows would continue to work.
