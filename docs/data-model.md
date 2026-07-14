# Data Model

This document describes the Phase 1 persistence schema introduced for metadata
collection and organization.

Phase 1 uses SQLite with SQLAlchemy 2.x mappings and Alembic migrations. Alembic is
the normal schema creation and migration path; application code should not create the
schema with `Base.metadata.create_all()`.

## Tables

### `videos`

Stores one row per public YouTube video known to the project.

- `id`: internal integer primary key.
- `youtube_video_id`: non-null unique YouTube video ID.
- `first_seen_at`: non-null UTC timestamp for when the project first discovered the
  video.

The unique `youtube_video_id` constraint prevents duplicate video rows when the same
video is found by repeated or different searches.

### `youtube_video_metadata`

Stores the latest YouTube-owned metadata for one video.

- `id`: internal integer primary key.
- `video_id`: non-null unique foreign key to `videos.id`.
- `title`: non-null YouTube title.
- `description`: optional YouTube description.
- `channel_id`: non-null YouTube channel ID.
- `channel_title`: non-null YouTube channel title.
- `published_at`: optional UTC publication timestamp.
- `duration_seconds`: optional non-negative duration.
- `view_count`: optional non-negative view count.
- `like_count`: optional non-negative like count.
- `comment_count`: optional non-negative comment count.
- `tags`: non-null JSON array of YouTube tags.
- `thumbnail_url`: optional thumbnail URL.
- `video_url`: optional canonical video URL.
- `last_refreshed_at`: non-null UTC timestamp for the latest metadata refresh.

This table is one-to-one with `videos`.

### `search_queries`

Stores search terms and search parameters used for discovery.

- `id`: internal integer primary key.
- `query_text`: non-null search text.
- `parameters`: non-null JSON object of project-owned search parameters.
- `parameters_fingerprint`: non-null stable fingerprint of the parameters.
- `created_at`: non-null UTC timestamp for when the query record was created.

The unique constraint on `(query_text, parameters_fingerprint)` allows the same text
with different parameters to be represented while avoiding duplicate query records for
the same logical search.

### `collection_runs`

Stores a single collection attempt for a stored search query.

- `id`: internal integer primary key.
- `search_query_id`: non-null foreign key to `search_queries.id`.
- `started_at`: non-null UTC timestamp.
- `completed_at`: optional UTC timestamp.
- `status`: non-null run status string.
- `error_message`: optional sanitized error message.

Collection runs preserve when a search was performed. A search query can have many
collection runs.

### `search_hits`

Stores the fact that one collection run returned one stored video.

- `id`: internal integer primary key.
- `collection_run_id`: non-null foreign key to `collection_runs.id`.
- `video_id`: non-null foreign key to `videos.id`.
- `discovered_at`: non-null UTC timestamp for the hit.
- `rank`: optional positive rank within the search results.

`search_hits` intentionally does not store `search_query_id`; the query is reached
through `collection_runs.search_query_id`. This avoids duplicated relationship data
that could become inconsistent.

The relationship path is:

```text
search_queries -> collection_runs -> search_hits -> videos
```

### `research_annotations`

Stores researcher-owned review fields separately from YouTube metadata.

- `id`: internal integer primary key.
- `video_id`: non-null unique foreign key to `videos.id`.
- `review_status`: non-null manual review status.
- `notes`: optional researcher notes.
- `relevance_label`: optional relevance label.
- `competition_name`: optional competition name.
- `fencer_names`: non-null JSON array of fencer names.
- `weapon_category`: optional weapon category.
- `event_notes`: optional event or tournament notes.
- `updated_at`: non-null UTC timestamp.

Annotations are not stored in `youtube_video_metadata`, so metadata refreshes do not
overwrite researcher review work.

Milestone 7 adds CLI commands for manual review using this existing table. The
commands can show annotation fields, set `review_status`, set `notes`, set the single
`relevance_label`, and clear `relevance_label`.

`review_status` is a workflow status and currently accepts only `unreviewed` and
`reviewed`. Research relevance or category information belongs in `relevance_label`.
The current schema stores one `relevance_label` string, not a list of labels. True
multi-label support is intentionally postponed because it would require a schema
migration and a separate data-compatibility decision.

## Provenance Strategy

The schema preserves discovery provenance by storing search terms in `search_queries`,
collection timing in `collection_runs`, returned-video relationships in `search_hits`,
and video identity plus `first_seen_at` in `videos`.

If a duplicate YouTube video ID is discovered again, the existing `videos` row should
be reused by later repository code. A new `search_hits` row can still record the new
collection-run relationship.

## Metadata Strategy

Phase 1 stores latest YouTube metadata plus collection-run provenance. It does not
store historical metadata snapshots yet.

This keeps the initial schema practical while still preserving when and how videos
were discovered. Metadata snapshots are postponed because they add storage growth,
export semantics, and migration complexity. If future research requires reconstructing
past title, description, tag, or count values, a dedicated snapshot table should be
added in a later migration and ADR.

## SQLite First, PostgreSQL Later

SQLite is the Phase 1 database. The schema uses generic SQLAlchemy column types,
named constraints, and ordinary relational keys so a later PostgreSQL migration remains
possible.

SQLite-specific behavior is kept in infrastructure helpers, such as enabling foreign
keys on SQLite connections and normalizing datetimes for SQLite storage.

## UTC Datetimes

Persistence code uses an infrastructure-only `UTCDateTime` SQLAlchemy type. It rejects
naive datetimes, normalizes aware datetimes to UTC, stores SQLite values as UTC, and
returns timezone-aware UTC `datetime` objects.

Domain models also require UTC-aware datetimes, so repositories added later should map
database values directly into domain objects without losing timezone information.

## JSON Fields

JSON is used only for flexible structured fields:

- `search_queries.parameters`
- `youtube_video_metadata.tags`
- `research_annotations.fencer_names`

These fields are not critical relational identity fields. Critical integrity rules
remain in relational columns, foreign keys, unique constraints, and check constraints.
SQLAlchemy's `JSON` type keeps the design portable enough for SQLite now and
PostgreSQL later.

## Not Implemented Yet

## Repository And Unit Of Work Boundaries

Milestone 2B adds repository ports and SQLAlchemy implementations for the Phase 1
tables. Repository ports expose domain models and lightweight typed persistence
handles, not SQLAlchemy sessions, ORM classes, or raw database integers.

The repository groups are intentionally small:

- video persistence and latest YouTube metadata;
- search queries, collection runs, and search hits;
- researcher annotations.

The Unit of Work opens one SQLAlchemy session per transaction. It commits only when
called explicitly, rolls back on exceptions, rolls back when a caller exits without
committing, and always closes the session.

Repository code preserves the schema relationship path:

```text
search_queries -> collection_runs -> search_hits -> videos
```

`search_hits` does not use `search_query_id` directly.

## Not Implemented Yet

The project does not yet implement exports, pandas export logic, video downloading,
computer vision, event detection, scoring detection, web UI, cloud deployment, or
metadata snapshot history.
