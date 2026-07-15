# ADR-0010: Search-hit provenance export

## Status

Accepted

## Context

The project can collect YouTube metadata, store search provenance, inspect stored
videos and collection runs, manually annotate videos, and export one row per stored
video to CSV or JSON.

The video-level export is useful for review and general analysis, but it compresses
discovery history. A video can be returned by multiple searches and collection runs.
Researchers need an export that preserves each search-hit relationship for auditing
which query and run returned which video, with rank and timing.

## Decision

Add a Typer command:

```powershell
fencing-video-research-agent export search-hits
```

The command writes one row per `search_hits` row to CSV or JSON:

- default CSV path: `data/exports/search_hits.csv`
- default JSON path: `data/exports/search_hits.json`
- optional `--format csv|json`
- optional `--output PATH`
- optional `--overwrite`
- optional `--database-url`

The export includes collection-run provenance, query text and parameters, search-hit
rank and discovery time, video identity, useful latest metadata, and a small
annotation summary. It intentionally includes `review_status` and `relevance_label`
only from annotations; long researcher notes remain in the video-level export.

CSV exports encode `query_parameters` as a JSON string. JSON exports preserve
`query_parameters` as an object.

## Alternatives considered

- Add search-hit rows to the existing `export videos` dataset.
- Export all annotation fields, including long notes.
- Add a generic export framework for every future dataset.
- Store a new provenance snapshot table before exporting.

## Reasons for rejection

Adding search-hit rows to the video-level export would mix two dataset grains and make
row meaning ambiguous. Exporting long notes would make the provenance dataset noisy
and could expose more manual review text than needed for auditing. A generic export
framework would add abstraction before there are enough dataset shapes to justify it.
A new provenance table is unnecessary because the existing schema already stores the
relationship path:

```text
search_queries -> collection_runs -> search_hits -> videos
```

## Consequences

Researchers can export discovery provenance without losing repeated appearances of
the same video across different collection runs. Generated search-hit exports remain
ignored by Git under `data/exports/`.

The project now has two export dataset contracts:

- `export videos`: one row per stored video.
- `export search-hits`: one row per search-hit relationship.

Future export additions should keep dataset grain explicit.

## Performance impact

The search-hit export reads search-hit rows and related query, run, video metadata,
and annotation summary fields into a pandas DataFrame. This is appropriate for the
SQLite-first Phase 1 dataset. If search-hit exports become large, later milestones can
add chunking based on measured need.

## Security impact

The command does not call YouTube, does not instantiate the YouTube client, and does
not require `YOUTUBE_API_KEY`. It prints only the output path, row count, and format.
It must not print API keys, `.env` contents, raw SQL, raw Google responses, stack
traces, or exported records.

## Migration and compatibility

No database migration is introduced. The export uses the existing Phase 1 schema and
does not modify stored database data. Existing collection, inspection, annotation, and
video-level export commands remain compatible.

## Reversibility

The workflow can be reverted by removing the search-hit export use case, port DTOs,
SQLAlchemy reader, pandas writer, CLI command, tests, and documentation updates. No
database rollback is required because no schema changes are introduced.
