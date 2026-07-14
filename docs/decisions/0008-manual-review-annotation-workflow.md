# ADR-0008: Manual review annotation workflow

## Status

Accepted

## Context

The project can collect official YouTube metadata, persist videos and collection
provenance, and inspect stored videos and collection runs through the CLI. The Phase 1
schema already includes a `research_annotations` table for researcher-owned review
fields kept separate from YouTube metadata.

Researchers need a small manual workflow for reviewing stored videos without calling
YouTube again, changing YouTube-owned metadata, or requiring an API key.

## Decision

Add a Typer `annotations` command group for local manual review:

- `annotations show <youtube_video_id>`
- `annotations set-status <youtube_video_id> <status>`
- `annotations set-notes <youtube_video_id> --notes "..."`
- `annotations set-label <youtube_video_id> <label>`
- `annotations clear-label <youtube_video_id>`

The workflow uses application-layer use cases, the existing repository ports, and the
existing Unit of Work. The CLI loads settings with `require_youtube_api_key=False`,
runs Alembic migration checks, builds a database-only annotation runtime, and calls
the application use cases.

`ReviewStatus` remains limited to the existing workflow values: `unreviewed` and
`reviewed`. Research relevance or category information is stored in the existing
single `research_annotations.relevance_label` field.

## Alternatives considered

- Add true multi-label support now.
- Store multiple labels in `relevance_label` with a delimiter.
- Reuse the collection runtime for annotation commands.
- Let the CLI write annotations directly through SQLAlchemy repositories.

## Reasons for rejection

True multi-label support requires a schema migration and a separate compatibility
decision. Delimiter-based labels would hide structure inside a string and make later
data migration ambiguous. Reusing the collection runtime would unnecessarily require
YouTube composition paths for local annotation commands. Direct CLI repository access
would put workflow and transaction rules in the interface layer instead of the
application layer.

## Consequences

Researchers can review and annotate videos already stored in the local database. The
workflow preserves unrelated annotation fields when one field is updated and leaves
YouTube-owned metadata untouched.

The current label workflow is intentionally single-label only. Future true multi-label
support should add a schema migration, data documentation, tests, and a new ADR.

## Performance impact

Annotation commands perform small local database reads and writes against one video at
a time. They do not add network calls, caching, concurrency, or bulk processing.

## Security impact

Annotation commands do not require `YOUTUBE_API_KEY`, do not instantiate the YouTube
client, and do not call YouTube. Command output must not print secrets, `.env`
contents, raw SQL, raw Google responses, or stack traces.

## Migration and compatibility

No schema migration is introduced. The workflow uses the existing
`research_annotations` table and the existing `relevance_label` column. Missing video
IDs create no annotation rows.

Existing collection, inspection, and metadata-refresh behavior remains compatible.
Metadata refreshes continue to leave researcher annotations untouched.

## Reversibility

The workflow can be reverted by removing the annotation application use cases, CLI
commands, tests, documentation updates, and annotation runtime wiring. No database
rollback is required because no schema changes are introduced.
