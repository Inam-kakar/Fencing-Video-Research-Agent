# ADR-0002: SQLite SQLAlchemy Alembic persistence foundation

## Status

Accepted

## Context

The project is a Phase 1 research application for collecting and organizing public
fencing-video metadata. Project instructions require Python 3.12, SQLAlchemy 2.x,
Alembic, SQLite first, PostgreSQL later, deterministic offline tests, and a lightweight
clean architecture.

Milestone 1 established framework-free domain models and project-owned YouTube port
types. It deliberately excluded persistence, migrations, repositories, and Unit of
Work. Milestone 2A introduces only the database schema and migration foundation.

## Decision

Use SQLAlchemy 2.x declarative ORM mappings in the infrastructure layer, SQLite as the
Phase 1 database, and Alembic as the normal schema migration path.

The initial schema contains:

- `videos`
- `youtube_video_metadata`
- `search_queries`
- `collection_runs`
- `search_hits`
- `research_annotations`

`search_hits` links collection runs to videos. It does not duplicate
`search_query_id`; the query is reached through the collection run.

The schema stores latest YouTube metadata plus collection-run provenance. Researcher
annotations are stored separately from YouTube metadata. Metadata snapshot history is
postponed.

Repositories and Unit of Work are postponed to Milestone 2B so the schema can be
reviewed and validated before transaction APIs are added.

## Alternatives considered

- Use raw SQL without SQLAlchemy mappings.
- Use SQLAlchemy `Base.metadata.create_all()` as the normal schema strategy.
- Store metadata snapshots immediately.
- Add repositories and Unit of Work in the same milestone as the schema.
- Add PostgreSQL-specific types or behavior now.

## Reasons for rejection

Raw SQL would make repository mapping and later schema comparison harder. Using
`create_all()` as the normal schema path conflicts with the project instruction to use
Alembic for persistent schema changes. Metadata snapshots add complexity before a
confirmed Phase 1 need. Adding repositories and Unit of Work immediately would make the
milestone too large for careful review. PostgreSQL-specific behavior is premature while
SQLite is the active Phase 1 database.

## Consequences

The project gains a reproducible relational schema with named constraints, Alembic
migration files, SQLite migration tests, and data-model documentation.

Application code still cannot collect, store, or query videos through repositories
until Milestone 2B adds repository and Unit of Work boundaries.

## Performance impact

The schema adds indexes for known lookup and filtering paths: YouTube video IDs,
search query text, collection-run query references, search-hit relationships,
metadata refresh time, and annotation review fields. These indexes support expected
Phase 1 workflows without adding speculative caching or concurrency.

## Security impact

No secrets are introduced, read, stored, printed, or logged. The schema can store
sanitized collection-run error messages, but future code must ensure API keys and
other credentials are never written there.

## Migration and compatibility

This is the first persistent schema migration, so there is no prior database schema to
upgrade. The migration can be downgraded to `base`, removing the Phase 1 application
tables. Future schema changes must be added as new Alembic revisions rather than
editing this migration after it is applied.

The schema uses generic SQLAlchemy types and named constraints to keep later
PostgreSQL migration practical. JSON is limited to flexible structured metadata
fields, while core identity and provenance remain relational.

## Reversibility

Before application data exists, the migration can be reversed with Alembic downgrade
to `base`. After real research data exists, rollback requires backing up the SQLite
database first because downgrade removes the Phase 1 tables and their data.

