# Fencing Video Research Agent

A Python research application for discovering, collecting, organizing, and reviewing
public fencing-video metadata through the official YouTube Data API.

The initial research focus is sabre fencing.

## Current phase

The project is currently in Phase 1: video discovery and metadata collection.

Phase 1 will:

- Search YouTube for videos related to selected fencers and competitions.
- Retrieve public metadata through the official YouTube Data API.
- Store videos, search queries, search results, and collection runs.
- Preserve when and how each video was discovered.
- Support manual researcher review.
- Export selected data to CSV and JSON.

## Phase 1 non-goals

Phase 1 does not include:

- Video downloading
- YouTube webpage scraping
- Computer vision
- Scoring-action detection
- Video segmentation
- Automatic event classification
- Model training
- A web frontend
- Cloud deployment

## Technology stack

- Python 3.12
- YouTube Data API v3
- google-api-python-client
- SQLAlchemy 2.x
- Alembic
- SQLite
- pandas
- Typer
- Pydantic
- pytest
- Ruff
- mypy

## Architecture

The project uses a lightweight clean architecture:

- `domain`: research concepts and business rules
- `application`: use cases and workflows
- `ports`: interfaces for external capabilities
- `infrastructure`: YouTube, SQLAlchemy, SQLite, files, and exports
- `interfaces`: command-line interface
- `bootstrap`: dependency construction

External libraries must not become dependencies of the domain layer.

## Repository structure

```text
src/fencing_video_research_agent/
tests/
docs/
docs/decisions/
data/