# ADR-0009: Pandas-backed export workflow

## Status

Accepted

## Context

The project can collect official YouTube metadata, store collection provenance,
inspect stored videos and collection runs, and manually annotate stored videos. Phase
1 also requires CSV and JSON exports for reproducible research workflows.

Pandas is already part of the approved project stack for tabular processing and
export operations. Generated research data under `data/exports/` is ignored by Git
while `data/exports/.gitkeep` keeps the directory available in the repository.

## Decision

Add a Typer `export videos` command that writes one row per stored video to CSV or
JSON:

- default CSV path: `data/exports/videos.csv`
- default JSON path: `data/exports/videos.json`
- optional `--output PATH`
- optional `--overwrite`
- optional `--database-url`

The export includes latest YouTube metadata, manual annotation fields, and compact
collection provenance summary fields. The command loads settings without requiring
`YOUTUBE_API_KEY`, runs Alembic migration checks, reads from the local database, and
writes the output file through a pandas-backed infrastructure writer.

## Alternatives considered

- Export search-hit/provenance rows in the same milestone.
- Put pandas directly in the application use case.
- Extend the display-oriented `StoredDataReader`.
- Overwrite existing files by default.
- Print exported records to the terminal.

## Reasons for rejection

Search-hit exports are useful but would add a second dataset contract and make the
first export milestone larger. Pandas belongs in infrastructure because it is an
external tabular/file dependency, while application code should coordinate ports.
`StoredDataReader` is shaped for CLI inspection, not complete export datasets.
Overwriting by default risks losing research artifacts. Printing exported records
would be noisy and could expose notes or large descriptions unnecessarily.

## Consequences

Researchers can produce analysis-ready CSV or JSON files after collecting and
annotating videos. Generated exports remain outside Git by default. CSV exports encode
structured fields such as tags and fencer names as JSON strings, while JSON exports
preserve those fields as arrays.

The first export is video-level only. A later milestone can add one-row-per-search-hit
or richer provenance datasets with their own tests and documentation.

## Performance impact

The export reads all stored videos into a pandas DataFrame. This is appropriate for
the small SQLite-first Phase 1 dataset. If exports become large, later milestones can
add chunking or streaming based on measured need.

## Security impact

The export command does not call YouTube, does not instantiate the YouTube client, and
does not require `YOUTUBE_API_KEY`. It prints only the output path, row count, and
format. It must not print API keys, `.env` contents, raw SQL, raw Google responses,
stack traces, or full exported records.

## Migration and compatibility

No database migration is introduced. The export uses the existing Phase 1 schema and
does not modify stored database data. Existing collection, inspection, and annotation
commands remain compatible.

## Reversibility

The workflow can be reverted by removing the export use case, export ports,
SQLAlchemy export reader, pandas writer, CLI command, tests, and documentation
updates. No database rollback is required because no schema changes are introduced.
