# Project Brief: Fencing Video Research Agent

## Objective

Build a reproducible Python application for collecting, organizing, reviewing, and
exporting public fencing-video metadata.

The initial research focus is sabre fencing.

Phase 1 is a metadata collection and organization system. It is not a video-analysis,
computer-vision, or machine-learning system.

## Research purpose

The project supports fencing-video research by helping collect and preserve information
about public YouTube videos in a structured local database.

The system should make it clear:

- Which search terms were used
- When each search was performed
- Which videos were discovered by each search
- Which metadata was collected
- When metadata was collected or refreshed
- Which videos were manually reviewed
- Which researcher annotations were added

## Phase 1 scope

Phase 1 includes:

- Searching YouTube through the official YouTube Data API
- Collecting video metadata
- Storing metadata in a local relational database
- Recording collection runs and search terms
- Preserving relationships between searches and videos
- Supporting manual review status and researcher annotations
- Exporting selected results to CSV and JSON
- Running deterministic automated tests without live API access

## Phase 1 non-goals

Phase 1 does not include:

- YouTube webpage scraping
- Video downloading
- Computer vision
- Event detection
- Scoring-action detection
- Winner classification
- Model training
- Web frontend
- Mobile application
- Cloud deployment
- Multi-user authentication

## Required metadata

The system should collect and store relevant YouTube metadata such as:

- YouTube video ID
- Title
- Description
- Channel ID
- Channel title
- Publication date
- Duration
- View count
- Like count, when available
- Comment count, when available
- Tags, when available
- Thumbnail URL, when available
- Video URL
- Collection timestamp
- Last refresh timestamp

Missing optional metadata must be represented explicitly and must not cause silent data loss.

## Provenance requirements

The system must record:

- Search query text
- Search parameters
- Collection run timestamp
- Videos returned by each query
- First-seen timestamp for each video
- Last-refreshed timestamp for each video
- Filtering criteria used during collection or export

A video may appear in multiple searches. The system must preserve every search-to-video
relationship.

## Research annotations

Researcher annotations must be stored separately from YouTube metadata.

Metadata refresh must not overwrite researcher annotations.

Possible annotations include:

- Review status
- Research notes
- Relevance labels
- Competition information
- Fencer names, when known
- Weapon category
- Event or tournament notes

## Database direction

Use SQLite for Phase 1.

Use SQLAlchemy 2.x for ORM and database access.

Use Alembic for persistent schema migrations.

The database design should keep future migration to PostgreSQL possible without making
Phase 1 unnecessarily complex.

## Application interface

The Phase 1 user interface is a Typer command-line interface.

The CLI should support workflows such as:

- Collect videos for a search query
- Refresh metadata for stored videos
- List stored videos
- Review or annotate a video
- Export results
- Inspect collection history

## Reproducibility

The project must prioritize reproducibility.

Automated tests must not call the live YouTube API by default.

Tests should use:

- Fake ports
- Mocked API clients
- Fabricated API responses
- Temporary SQLite databases
- Temporary filesystem directories
- Fixed clocks where time affects behavior

## Example video

Example public fencing video URL:

https://m.youtube.com/watch?v=9Dyrylpso04

The example is useful for thinking about metadata structure, but implementation must not
hardcode this video.

## Completion criteria for Phase 1

Phase 1 is successful when the project can:

1. Search YouTube through the official API.
2. Store videos without duplicates.
3. Preserve multiple search-to-video relationships.
4. Record collection runs and search parameters.
5. Refresh metadata without deleting annotations.
6. Support manual review fields.
7. Export selected metadata and annotations.
8. Run tests, linting, formatting checks, and type checks successfully.
9. Avoid exposing secrets.
10. Provide clear documentation for setup and usage.
