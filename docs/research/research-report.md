# Fencing Video Research Agent: A Reproducible Metadata Collection System for Public Fencing Videos

Repository name: `Fencing-Video-Research-Agent`

Current phase: Phase 1 backend/research data foundation

Implementation state: Through Milestone 10A

Date generated: 2026-07-15

Author: Inam Ullah

## Project Summary

The Fencing Video Research Agent is a Python research software project for collecting,
organizing, reviewing, and exporting public fencing-video metadata in a reproducible
way. The current implementation focuses on sabre-related YouTube metadata collection
through the official YouTube Data API, local relational storage with SQLite,
controlled schema evolution with Alembic, manual command-line annotation, read-only
inspection of stored videos and collection runs, professional README/demo
documentation, pandas-backed CSV/JSON export of stored video records, and
search-hit/provenance CSV/JSON export. It is a backend and research-data foundation.
It does not yet
perform video downloading, computer vision, scoring detection, event detection,
frontend visualization, PostgreSQL deployment, or model training.

## Abstract

Public fencing and sabre videos are useful sources for future sports-video research,
but the metadata around those videos is scattered across public platforms and can be
difficult to collect in an auditable way. Manual search sessions and ad-hoc
spreadsheets do not reliably preserve which query was used, when it was run, which
videos were returned, or which metadata was collected at that time. This project
addresses the first stage of that problem by implementing a reproducible metadata
collection and organization system for public fencing videos.

The current system uses the official YouTube Data API v3 to search for public videos
and fetch metadata. It stores video identities, latest YouTube metadata, search
queries, collection runs, search hits, and separate research annotation fields in a
local SQLite database managed by SQLAlchemy and Alembic. The command-line interface
currently supports controlled collection, read-only video inspection, read-only
collection-run inspection, manual annotation updates, video-level CSV/JSON export,
and search-hit/provenance CSV/JSON export. Automated tests are offline and
deterministic, while real YouTube API use is limited to manual smoke testing. A real
smoke test with the query
`sabre fencing final` and `--max-results 5` succeeded, creating a local SQLite
database with five stored videos, one search query, one collection run, and five
search hits. Later local export verification produced video-level files and
search-hit provenance files from that same small database. This validates the current
backend workflow, but it is not yet a large scientific dataset or an AI
video-analysis system.

## Motivation and Problem Statement

Fencing video data is scattered across public platforms, especially YouTube. A
researcher interested in sabre bouts, competitions, athletes, or tactical patterns may
begin by searching manually, opening videos, copying links, and keeping notes in a
spreadsheet. That approach can work for casual exploration, but it is difficult to
audit and reproduce. It often fails to preserve the exact search terms, search
parameters, run times, result order, and metadata state at the time of collection.

Ad-hoc spreadsheets also make it harder to build a reliable foundation for future
research. If later work involves annotation, export, computer vision, event detection,
or scoring analysis, the project first needs a trustworthy record of what videos were
found and how they were found. Without that foundation, advanced analysis risks being
built on inconsistent or poorly documented data.

The project therefore starts with metadata collection, provenance, and storage before
advanced AI. This is intentionally modest but important: it turns public video search
from an informal manual process into a controlled, repeatable workflow that records
queries, timestamps, returned videos, and metadata.

## Research Objectives

The Phase 1 objectives are:

- Collect public fencing-video metadata using the official YouTube Data API.
- Avoid YouTube webpage scraping.
- Store video metadata in a relational database.
- Record query terms, parameters, collection run times, and search-hit relationships.
- Make the collection process reproducible and auditable.
- Provide local command-line inspection of stored videos and collection runs.
- Support manual review annotations that remain separate from YouTube metadata.
- Export stored video records and search-hit provenance records for later analysis
  and reporting.
- Prepare a foundation for later richer annotation, quality checks, controlled
  collection protocols, and video-AI research.

The Phase 1 non-objectives are equally important:

- No video downloading yet.
- No computer vision yet.
- No event detection yet.
- No scoring detection yet.
- No winner prediction yet.
- No frontend UI yet.
- No PostgreSQL deployment yet.
- No conference or scientific conclusion is claimed from the current small smoke test.

## Scope Through Milestone 10A

Through Milestone 10A, the repository implements a backend data foundation with:

- Project setup as a Python 3.12 package.
- `AGENTS.md` engineering rules for architecture, testing, security, and scope.
- Framework-free domain models for videos, metadata, search queries, collection runs,
  search hits, and research annotations.
- A project-owned YouTube gateway port that keeps raw Google API dictionaries out of
  the domain and application layers.
- SQLAlchemy ORM mappings and an Alembic migration for the Phase 1 metadata schema.
- Repository and Unit of Work boundaries for transactional writes.
- A collection use case tested first with fake YouTube gateway objects.
- A concrete official YouTube Data API adapter in infrastructure.
- A Typer CLI `collect` command for controlled metadata collection.
- A manual real-API smoke test that succeeded with five results.
- Read-only `videos list` and `videos show <youtube_video_id>` commands.
- Read-only `runs list` and `runs show <run_id>` commands.
- Manual annotation commands for showing annotations, setting review status, setting
  notes, setting one relevance label, and clearing that label.
- A pandas-backed `export videos` command for CSV and JSON output.
- A pandas-backed `export search-hits` command for search-hit/provenance CSV and
  JSON output.
- A professional README/demo guide that explains setup, architecture, commands,
  validation, documentation links, roadmap, and project status.
- Offline automated tests, linting, formatting checks, type checks, and architecture
  boundary scans.

The project does not yet implement metadata snapshot history, video downloading,
computer vision, scoring detection, event detection, web UI, cloud deployment,
PostgreSQL operation, or a large scientific dataset.

## Methodology

The project uses incremental milestone-based development. Each milestone introduces a
small coherent piece of functionality, validates it with tests, documents the relevant
architecture decision, and avoids unrelated refactoring. This method reduces risk
because design decisions are reviewed before implementation and because each layer is
tested before later layers depend on it.

The methodology is based on a lightweight clean architecture style:

- Domain models are plain Python objects.
- Application use cases coordinate workflows.
- Ports define external boundaries.
- Infrastructure implements those ports with SQLAlchemy, Alembic, Google API clients,
  settings, and local database access.
- The Typer CLI remains a thin interface.
- `bootstrap.py` is the composition root where concrete dependencies are wired.

The project deliberately used fake YouTube gateway tests before adding the real
YouTube adapter. This made collection behavior testable without internet access,
quota usage, or a real API key. The official adapter was added later, behind the same
gateway interface. SQLite was chosen first because it keeps early research workflows
local and reproducible. Alembic migrations were introduced early so database structure
has a controlled history rather than relying on manual table creation.

Validation is performed before completing milestones. The normal suite is offline and
deterministic. Real API calls are treated as manual smoke tests, not ordinary
automated tests.

## System Architecture

The current architecture can be summarized as:

```text
CLI
-> Application Use Cases
-> Ports / Interfaces
-> Infrastructure Adapters
-> SQLite Database / YouTube Data API
```

### Domain

The domain layer contains framework-free research concepts such as `Video`,
`YouTubeMetadata`, `SearchQuery`, `CollectionRun`, `SearchHit`,
`ResearchAnnotation`, and `ReviewStatus`. These models validate basic invariants such
as non-empty video IDs, UTC-aware timestamps, positive ranks, and non-negative counts.
They do not import SQLAlchemy, Alembic, Typer, Google libraries, pandas, dotenv, or
environment-variable code.

### Application

The application layer contains use cases. The main collection use case coordinates
YouTube search, metadata enrichment, deduplication, collection-run creation, video
storage, search-hit recording, and Unit of Work commit. The inspection use cases list
or show stored videos and collection runs through read-only ports. Annotation use
cases update researcher-owned fields through repository ports. The export use cases
coordinate video-level export records, search-hit provenance export records, and file
writing through export ports.
Application code does not construct SQLAlchemy sessions, call Google clients directly,
use pandas directly, or parse raw Google API dictionaries.

### Ports

Ports define project-owned boundaries. The YouTube gateway port exposes
`YouTubeSearchRequest`, `YouTubeSearchResult`, project-owned metadata, and typed
gateway errors. Repository and Unit of Work ports define persistence boundaries for
writes. The stored-data reader port defines read-only projections for local
inspection. Export ports define video export and search-hit provenance export reader
and writer boundaries so pandas stays in infrastructure.

### Infrastructure

Infrastructure contains concrete technical implementations:

- Official YouTube Data API adapter.
- SQLAlchemy ORM mappings.
- SQLAlchemy repositories.
- SQLAlchemy read repositories.
- SQLite engine/session helpers.
- Alembic migration runner.
- Pydantic settings.
- Pandas-backed CSV and JSON export behavior for video-level and search-hit
  provenance datasets.
- System clock.

SQLAlchemy stays in infrastructure so the domain and application layers remain
independent of the database framework. This keeps the core workflow testable with
fakes and makes a later database change more manageable.

### Interface / CLI

The Phase 1 interface is a Typer command-line application. The CLI parses arguments,
loads settings, runs migrations, calls use cases, prints concise output, and maps
known failures to safe messages and exit codes. Collection commands require
YouTube configuration; local inspection, annotation, and export commands do not
require `YOUTUBE_API_KEY`. The CLI does not contain raw SQL, database session
construction, direct YouTube API calls, pandas export logic, or business rules.

### Persistence and Migrations

Persistence uses SQLAlchemy 2.x ORM mappings. Alembic is the normal schema creation
and migration path. After migrations were introduced, the project does not use
`Base.metadata.create_all()` as the normal application schema strategy.

## Data Model and Provenance

The database design records not only videos, but also how each video was discovered.
That is the central reproducibility feature of the current system.

### `videos`

The `videos` table stores one row per known public YouTube video. It contains the
unique YouTube video ID and `first_seen_at`, the UTC time when the project first
discovered the video. The unique video ID prevents repeated collection from creating
duplicate video rows.

### `youtube_video_metadata`

The `youtube_video_metadata` table stores the latest YouTube-owned metadata for one
video: title, description, channel, publication time, duration, view count, like
count, comment count, tags, thumbnail URL, video URL, and `last_refreshed_at`. It is
separate from `videos` so identity and latest metadata are clearly separated.

### `search_queries`

The `search_queries` table stores the search text and project-owned search
parameters. It also stores a stable parameter fingerprint so repeated equivalent
queries can be represented consistently. This table helps answer what the researcher
asked the system to search.

### `collection_runs`

The `collection_runs` table stores a single attempt to collect metadata for a stored
search query. It records the query reference, start time, completion time, status,
and an optional sanitized error message. This table helps answer when a search was
performed.

### `search_hits`

The `search_hits` table connects a collection run to the videos returned by that run.
It stores the collection run, video, discovery time, and optional rank. This table is
what preserves the fact that a specific search run returned a specific video.
`search_hits` intentionally does not store `search_query_id` directly; the query is
reached through the collection run:

```text
search_queries -> collection_runs -> search_hits -> videos
```

### `research_annotations`

The `research_annotations` table stores researcher-owned review fields separately
from YouTube metadata. This separation matters because metadata refreshes must not
overwrite researcher notes, review status, fencer names, or competition information.
Milestone 7 uses this existing table for manual review without a schema migration.
`ReviewStatus` remains limited to `unreviewed` and `reviewed`, and
`relevance_label` is intentionally a single label rather than a delimiter-based
multi-label field.

## YouTube Data Collection Process

A controlled collection run can be started with:

```powershell
fencing-video-research-agent collect "sabre fencing final" --max-results 5
```

The current collection process is:

1. The CLI loads local settings, including `YOUTUBE_API_KEY` from `.env`.
2. The CLI runs Alembic upgrade to `head` so the local database is ready.
3. The composition root wires the official YouTube adapter, SQLAlchemy engine,
   session factory, Unit of Work, clock, and application use case.
4. The use case sends a project-owned search request through the YouTube gateway.
5. The YouTube adapter calls `search.list` to discover candidate video IDs.
6. The use case deduplicates search result video IDs before metadata enrichment.
7. The adapter calls `videos.list` to fetch metadata for those IDs.
8. The use case saves videos, latest metadata, the search query, the collection run,
   and search-hit relationships in one Unit of Work.
9. The Unit of Work commits after the multi-step write succeeds.

The process is intentionally metadata-only. It does not download video files and does
not scrape YouTube webpages.

The collection process has two external API stages:

- Search step: find candidate YouTube video IDs using `search.list`.
- Metadata step: fetch detailed metadata for those IDs using `videos.list`.

## Read-Only Inspection Workflow

Milestones 6A and 6B added local inspection commands. These commands inspect the
SQLite database only. They do not call YouTube, do not require `YOUTUBE_API_KEY`, and
do not spend API quota.

Stored videos can be inspected with:

```powershell
fencing-video-research-agent videos list
fencing-video-research-agent videos show <youtube_video_id>
```

Collection runs can be inspected with:

```powershell
fencing-video-research-agent runs list
fencing-video-research-agent runs show <run_id>
```

This workflow supports verification. After a collection run, the researcher can see
which videos were stored and which collection run returned them. Missing video or run
IDs return safe not-found messages rather than raw stack traces.

## Manual Annotation Workflow

Milestone 7 added local annotation commands for researcher review. These commands
operate only on the local database. They do not call YouTube, do not require
`YOUTUBE_API_KEY`, and do not spend API quota.

Annotations can be inspected and updated with:

```powershell
fencing-video-research-agent annotations show <youtube_video_id>
fencing-video-research-agent annotations set-status <youtube_video_id> <status>
fencing-video-research-agent annotations set-notes <youtube_video_id> --notes "..."
fencing-video-research-agent annotations set-label <youtube_video_id> <label>
fencing-video-research-agent annotations clear-label <youtube_video_id>
```

The workflow is deliberately small. `ReviewStatus` remains limited to `unreviewed`
and `reviewed`. `relevance_label` is a single label only; the project intentionally
does not use delimiter tricks to store multiple labels in one string. Because the
Phase 1 schema already included `research_annotations`, this milestone did not need a
schema migration. YouTube-owned metadata remains separate from researcher-owned
annotation fields.

## Pandas-Backed Export Workflow

The project now supports two local export workflows. Both read only from the local
database, do not call YouTube, do not require `YOUTUBE_API_KEY`, and should not print
full exported records to the terminal.

| Command | Dataset Shape | Main Question Answered | Default Outputs |
| --- | --- | --- | --- |
| `export videos` | One row per stored video | What videos are stored? | `data/exports/videos.csv`, `data/exports/videos.json` |
| `export search-hits` | One row per discovery/search result event | How were those videos discovered? | `data/exports/search_hits.csv`, `data/exports/search_hits.json` |

Milestone 8 added the video-level export command:

```powershell
fencing-video-research-agent export videos
```

The command supports:

```text
--format csv|json
--output PATH
--overwrite
--database-url
```

The default output paths are:

```text
data/exports/videos.csv
data/exports/videos.json
```

The export writes one row per stored video. Each row includes YouTube metadata,
manual annotation fields, and compact provenance summary fields. CSV and JSON are the
first implemented research export formats. The export is pandas-backed in
infrastructure, while the application layer uses project-owned export ports.

Milestone 10A added the search-hit provenance export command:

```powershell
fencing-video-research-agent export search-hits
```

It supports the same core options:

```text
--format csv|json
--output PATH
--overwrite
--database-url
```

The default output paths are:

```text
data/exports/search_hits.csv
data/exports/search_hits.json
```

This export writes one row per search hit. Each row includes query/run provenance,
search-hit rank and discovery time, video identity, selected YouTube metadata,
`review_status`, and `relevance_label`. It does not include long annotation notes
because the purpose of this dataset is provenance and auditability rather than full
review text. It complements the video-level export by preserving repeated discovery
events rather than collapsing everything to one row per video.

Generated export files under `data/exports/` are ignored by Git except for the
directory placeholder.

## Key Engineering Decisions, Alternatives, and Lessons Learned

| Decision | Alternative Considered | Chosen Approach | Reason | Trade-off | What I Learned |
| --- | --- | --- | --- | --- | --- |
| Official YouTube Data API instead of scraping | Scrape YouTube webpages | Use official YouTube Data API v3 | The official API is more stable, ethical, reproducible, and aligned with platform rules | Requires API key setup and quota awareness | Reliable research data collection should prefer official interfaces |
| Metadata first instead of video downloading or computer vision first | Begin with CV or event detection immediately | Build metadata and provenance foundation first | Advanced AI needs organized metadata and discovery records | Current system does not analyze video content | Strong data infrastructure should come before model training |
| SQLite first instead of PostgreSQL first | Start with PostgreSQL | Use local SQLite for Phase 1 | SQLite is simple, local, reproducible, and low-friction for early research | Less suitable for multi-user or cloud deployment | Local-first databases reduce setup friction |
| SQLAlchemy ORM instead of raw SQL everywhere | Raw SQL scripts | SQLAlchemy ORM mappings in infrastructure | Clear mappings, portability, and maintainable persistence | Adds abstraction to learn | ORM helps organize database code but should stay out of domain/application |
| Alembic migrations instead of `create_all()` or manual schema edits | Create tables directly from models | Alembic migration history | Controlled schema evolution supports reproducibility | More setup and migration files | Research systems need auditable schema changes |
| Clean architecture and ports instead of direct CLI calls | Put all logic in CLI scripts | Domain, application, ports, infrastructure, CLI, bootstrap | Easier testing and replaceable adapters | More files and concepts | Separation of concerns prevents quick scripts from becoming unmaintainable |
| Fake gateway tests before real YouTube adapter | Test only against the live API | Test use case with fake gateway first | Tests remain offline, deterministic, and quota-free | Fake tests cannot catch every API behavior | External services should be isolated behind ports |
| Repository and Unit of Work pattern | Direct SQLAlchemy sessions everywhere | Repository ports and explicit Unit of Work | Transaction boundaries and rollback behavior are clear | More architecture | Explicit commit/rollback helps avoid partial writes |
| CLI first instead of frontend first | Build Streamlit or web UI immediately | Use Typer CLI as first interface | CLI proves backend workflow without UI complexity | Less accessible to non-technical users | Stable backend behavior should come before public interface |
| Read-only inspection before export/frontend | Jump to CSV export or UI | Add `videos` and `runs` inspection commands | Stored data and provenance should be verified before export | Output is plain and not yet demo-polished | Inspection is necessary before analysis/export |
| Single-label annotation before richer labeling | Add multi-label schema or delimiter strings immediately | Use existing `relevance_label` as one label | Avoids ambiguous string encoding and avoids a premature schema migration | Less expressive annotation for now | Annotation structure should evolve through schema decisions |
| Pandas-backed exports | Put pandas in application code | Keep pandas in infrastructure and expose export behavior through ports | Provides useful research files while preserving architecture boundaries | Export shapes must be kept explicit and documented | Export contracts are part of the research data design |
| Separate search-hit provenance export | Fold search-hit data into the video-level export only | Add `export search-hits` as a separate dataset | Video rows and discovery-event rows answer different research questions | Researchers must understand two related export files | Provenance deserves its own dataset contract |
| Professor-facing README and demo guide | Rely only on source code and ADRs | Polish README and demo documentation | Research software must be explainable and reviewable | Documentation requires maintenance as behavior changes | Professional software is not only implementation |
| Do not commit `.env` or local SQLite DB | Include local secrets or data in repo | Ignore `.env`, `.db`, `.sqlite`, and related local artifacts | Protects secrets and keeps repository clean | Users must recreate local data | Reproducibility should come from commands and docs, not committed secrets |

## Milestone-by-Milestone Development Log

### Milestone 0 / Setup

The project started with repository setup, package configuration, `AGENTS.md`,
`.env.example`, documentation structure, and a test foundation. This mattered because
the project is intended to grow as research software rather than a one-off script.
The milestone deliberately did not implement collection, persistence, or API calls.
The key lesson was that project rules and validation habits need to exist before the
codebase becomes complex.

### Milestone 1: Domain Models and YouTube Port

Milestone 1 introduced framework-free domain models and a project-owned YouTube port.
This mattered because it established the data concepts and prevented raw Google API
responses from entering the application core. The milestone deliberately did not add
database code, CLI commands, or a real adapter. The key lesson was that clean
contracts make later fake testing and real adapter implementation much safer.

### Milestone 2A: SQLAlchemy Schema and Alembic Migration

Milestone 2A added SQLAlchemy mappings, SQLite support, Alembic setup, an initial
migration, migration tests, data-model documentation, and ADR-0002. This mattered
because the project needed a reproducible relational schema before persistence
repositories could be useful. The milestone deliberately did not add repository APIs
or Unit of Work behavior. The key lesson was that schema review is easier when it is
separated from transaction and use-case logic.

### Milestone 2B: Repositories and Unit of Work

Milestone 2B added repository ports, SQLAlchemy repository implementations, typed
record IDs, and a SQLAlchemy Unit of Work. This mattered because multi-step writes
need explicit commit and rollback behavior. The milestone deliberately did not add
application collection orchestration or YouTube API access. The key lesson was that
typed persistence handles reduce confusion while still keeping database details out
of the domain.

### Milestone 3: Collection Use Case

Milestone 3 added the application-layer collection use case and fake gateway tests.
This mattered because it proved the workflow before introducing live external API
behavior. The milestone deliberately did not add the real Google adapter, CLI, or
live API calls. The key lesson was that a fake gateway can verify orchestration,
deduplication, missing metadata handling, and rollback behavior without internet
access.

### Milestone 4: Official YouTube Data API Adapter

Milestone 4 added the official YouTube Data API adapter, settings, system clock, API
response mapping, pagination, batching, error classification, and offline adapter
tests. This mattered because it connected the project-owned gateway port to the real
official API while keeping raw Google dictionaries in infrastructure. The milestone
deliberately did not add CLI commands or live automated tests. The key lesson was
that external service behavior should be converted at the boundary into project-owned
types.

### Milestone 5: CLI Composition and Controlled Collection

Milestone 5 added Typer CLI wiring, the composition root, runtime migration helper,
settings for database URL and logging, and a controlled `collect` command. It enabled
a real manual smoke test. The milestone deliberately did not add export, frontend, or
analysis features. The key lesson was that a CLI can validate the backend end to end
before a user-facing interface is built.

### Milestone 6A: Read-Only Video Inspection

Milestone 6A added `videos list` and `videos show <youtube_video_id>`. These commands
read local SQLite only, do not call YouTube, and do not require `YOUTUBE_API_KEY`.
This mattered because the researcher needed to inspect stored video records after
collection. The milestone deliberately did not add run inspection, annotation editing,
or exports. The key lesson was that read-only inspection is a separate concern from
collection and should use projection-shaped DTOs.

### Milestone 6B: Read-Only Collection-Run Inspection

Milestone 6B added `runs list` and `runs show <run_id>`. These commands expose
collection provenance: query text, parameters, timing, status, hit count, and returned
videos. This mattered because reproducibility depends on knowing not only which
videos exist, but how they were discovered. The milestone deliberately did not add
schema changes, metadata refresh, exports, or annotation editing. The key lesson was
that collection runs act as a research logbook for video discovery.

### Milestone 7: Manual Video Annotation Workflow

Milestone 7 added `annotations show <youtube_video_id>`,
`annotations set-status <youtube_video_id> <status>`,
`annotations set-notes <youtube_video_id> --notes "..."`,
`annotations set-label <youtube_video_id> <label>`, and
`annotations clear-label <youtube_video_id>`. These commands use the existing
`research_annotations` table and do not call YouTube or require `YOUTUBE_API_KEY`.
This mattered because researchers need a way to review stored videos without changing
YouTube-owned metadata. The milestone deliberately did not add a schema migration,
true multi-label support, delimiter-based labels, or video analysis. The key lesson
was that researcher review should remain local, explicit, and separate from metadata
refresh.

### Milestone 8: Pandas-Backed Video Export Workflow

Milestone 8 added `export videos` with `--format csv|json`, `--output PATH`,
`--overwrite`, and `--database-url`. The command writes one row per stored video to
`data/exports/videos.csv` or `data/exports/videos.json` by default, including latest
YouTube metadata, annotation fields, and compact provenance summary fields. It reads
the local database only and does not call YouTube or require `YOUTUBE_API_KEY`. This
mattered because collected and reviewed metadata can now leave the application as
analysis-ready research files. The milestone deliberately did not add search-hit-level
exports, frontend visualization, PostgreSQL deployment, or pandas dependencies in the
domain/application layers. The key lesson was that export behavior is a data contract
and should be introduced with a small, tested shape first.

### Milestone 9: README and Professor Demo Polish

Milestone 9 polished `README.md` into a structured professor-facing project guide.
It added or improved the table of contents, current capabilities, limitations,
architecture diagrams, data-flow diagram, tech stack, repository structure, setup
instructions, CLI demos, validation commands, documentation links, roadmap, and
project status. This milestone did not change source code, database schema,
collection behavior, or tests. It mattered because a research software project needs
clear public-facing documentation, not only working code. The key lesson was that
professional software is not only implementation; it must also be explainable,
reproducible, and reviewable.

### Milestone 10A: Search-Hit Provenance Export

Milestone 10A added `export search-hits` with `--format csv|json`, `--output PATH`,
`--overwrite`, and `--database-url`. The default outputs are
`data/exports/search_hits.csv` and `data/exports/search_hits.json`. The command
exports one row per search hit, including query/run provenance, search-hit rank and
discovery time, video identity, selected metadata, `review_status`, and
`relevance_label`. It does not include long annotation notes because this export is
primarily a provenance and audit dataset.

The command reads the local database only. It does not call YouTube, does not require
`YOUTUBE_API_KEY`, does not modify the database, and does not change the schema. It
complements video-level export: `export videos` answers what videos are stored,
while `export search-hits` answers how those videos were discovered. This matters
because research reproducibility depends on knowing not only the collected video set,
but also the query and collection-run context that produced each discovery. The key
lesson was that provenance should be exported as its own explicit dataset rather than
being compressed into a single video-level table.

## Validation and Testing

The normal automated tests are offline and deterministic. They use fake ports,
mocked or fabricated API clients, temporary SQLite databases, fixed clocks, and
Alembic-backed test databases. Real YouTube API calls are manual smoke tests only.

Current validation through Milestone 10A:

- `pytest`: 201 passed.
- `ruff check`: passed.
- `ruff format --check`: passed.
- `mypy src`: passed.
- Application/domain boundary scan: passed.
- Manual search-hit export smoke test: passed with five CSV rows and five JSON
  records from the existing small smoke-test database.

This matters for research reliability because the system can be changed and checked
without spending API quota, requiring internet access, or exposing secrets. It also
helps ensure that domain and application layers remain independent of infrastructure
details.

## Current Results

A real manual smoke test was performed with:

```powershell
fencing-video-research-agent collect "sabre fencing final" --max-results 5
```

The real official YouTube Data API collection succeeded. A local SQLite database was
created at the example local path:

```text
data/fencing_video_research.db
```

The initial post-collection smoke-test counts, before manual annotation commands were
tested, were:

| Table | Count |
| --- | ---: |
| `videos` | 5 |
| `youtube_video_metadata` | 5 |
| `search_queries` | 1 |
| `collection_runs` | 1 |
| `search_hits` | 5 |
| `research_annotations` | 0 |

The user-provided smoke-test facts listed these collected video IDs:

- `nGearEu2PlU`
- `CIcgdNm3Xmw`
- `s-DpKdeshUU`
- `x_7WnX0xPZg`
- `y96JkxTLIrU`

The read-only inspection commands were manually verified:

```powershell
fencing-video-research-agent videos list
fencing-video-research-agent videos show nGearEu2PlU
fencing-video-research-agent runs list
fencing-video-research-agent runs show 1
fencing-video-research-agent runs show 999999
```

Missing video or run lookups returned safe not-found messages. No API key was
printed. Later milestones added local annotation and export workflows on top of the
stored data. Manual export verification now includes `videos.csv` and `videos.json`
from the video-level export workflow, plus `search_hits.csv` and `search_hits.json`
from the provenance export workflow. The local search-hit export produced five
records from the existing small smoke-test database. Generated export files remain
ignored by Git and are not committed.

These results are a successful functional validation of the current backend workflow.
They are not a large dataset and should not be used to draw scientific conclusions
about fencing video content.

## Security, Ethics, and Reproducibility

The project uses the official YouTube Data API and avoids webpage scraping. It
collects public metadata only and does not download videos. API credentials are read
from local environment configuration and must not be committed. The `.gitignore`
configuration ignores `.env`, `.env.*`, database files such as `*.db` and `*.sqlite`,
and local data outputs. The `.env.example` file contains placeholders rather than
real credentials.

The manual smoke test is intentionally small to limit quota use. Automated tests do
not call the live YouTube API and do not require real API keys. Reproducibility is
supported by storing query text, query parameters, timestamps, collection runs,
search-hit relationships, researcher annotations, export contracts, schema
migrations, and validation tests. Annotation and export commands are local database
workflows and do not require YouTube credentials. Generated export files are ignored
by Git so local research artifacts do not become accidental source-control changes.

## Limitations

The current project has important limitations:

- The real smoke test contains only five videos.
- The system currently stores metadata, not video content.
- There is no computer vision or video analysis.
- There is no scoring-action detection.
- There is no event detection.
- There is no winner or outcome prediction.
- Annotation editing is implemented only as a focused manual CLI workflow; richer
  annotation structures may require later schema decisions.
- CSV and JSON export is implemented for video-level records and search-hit
  provenance records.
- There is no frontend UI.
- There is no PostgreSQL deployment yet.
- There is not yet a large scientific dataset.
- YouTube API quota limits and metadata availability affect collection.
- Search results can change over time, so each collection run must be timestamped and
  preserved as provenance.

## Future Work

### Short-Term

- Add richer annotation fields only if the research protocol needs them.
- Expand research documentation as the project grows.
- Add a repeatable small collection protocol for sabre-related searches.

### Medium-Term

- Add a frontend or dashboard after backend behavior is stable.
- Design a larger controlled collection protocol.
- Develop search query strategies for fencing and sabre topics.
- Add data quality checks for missing metadata, duplicate discovery paths, and
  incomplete records.
- Consider metadata snapshot history if refresh auditing becomes a research need.
- Add PostgreSQL configuration as an optional persistence target.

### Long-Term

- Build computer vision and event-detection experiments on top of the metadata
  foundation.
- Explore score or touch detection.
- Investigate fencer identification.
- Segment bouts into meaningful units.
- Study winner or outcome classification if appropriate data and labels exist.
- Develop a conference paper or poster around reproducible fencing video dataset
  construction and later video-analysis methods.

## Conference Presentation Potential

The current contribution is a reproducible metadata pipeline for public fencing
videos. It is not yet a final AI research contribution, but it is a necessary
foundation for one. Future research could build from this system toward a larger
curated fencing-video dataset, richer annotation protocols, data quality checks, and
eventually video-analysis methods. The system now includes both curated video-level
export and provenance/search-hit export, which makes it easier to separate questions
about what videos are stored from questions about how those videos were discovered.

Possible research questions include:

- How can public fencing video metadata be collected reproducibly?
- How does metadata quality affect downstream sports-video analysis?
- What provenance should be preserved before annotating public sports videos?
- How can public sports-video metadata be prepared for event detection and bout
  analysis?

The current project is suitable as a foundation for a conference poster or methods
discussion once it is expanded with larger controlled collections, richer annotation
protocols, data quality analysis, and possibly later video-analysis experiments.

## Glossary

Metadata: Descriptive information about a video, such as title, channel, publication
time, duration, tags, and counts.

Provenance: Information about where data came from and how it was collected.

Reproducibility: The ability to understand and repeat a process with documented
inputs, steps, and outputs.

API: Application Programming Interface, a structured way for software systems to
communicate.

YouTube Data API: The official Google API used here for YouTube search and video
metadata retrieval.

CLI: Command-line interface, a terminal-based way to run the application.

SQLite: A local relational database used as the first Phase 1 database.

SQLAlchemy: The Python ORM used to define database mappings and persistence logic.

Alembic: The migration tool used to version and apply database schema changes.

Repository: A persistence boundary that hides database details from application code.

Unit of Work: A transaction boundary that coordinates commit and rollback across
multiple repository operations.

Port: A project-owned interface that defines how application code talks to an
external capability.

Adapter: A concrete implementation of a port, usually in infrastructure.

Smoke test: A small manual test that verifies the main system path works end to end.

## Appendix

### Important Commands

Install and run the CLI through the package entry point:

```powershell
fencing-video-research-agent --help
```

Run a small controlled collection:

```powershell
fencing-video-research-agent collect "sabre fencing final" --max-results 5
```

Inspect stored videos:

```powershell
fencing-video-research-agent videos list
fencing-video-research-agent videos show <youtube_video_id>
```

Inspect collection runs:

```powershell
fencing-video-research-agent runs list
fencing-video-research-agent runs show <run_id>
```

Review stored videos locally:

```powershell
fencing-video-research-agent annotations show <youtube_video_id>
fencing-video-research-agent annotations set-status <youtube_video_id> <status>
fencing-video-research-agent annotations set-notes <youtube_video_id> --notes "..."
fencing-video-research-agent annotations set-label <youtube_video_id> <label>
fencing-video-research-agent annotations clear-label <youtube_video_id>
```

Export video-level research data:

```powershell
fencing-video-research-agent export videos --format csv
fencing-video-research-agent export videos --format json
```

Export search-hit provenance data:

```powershell
fencing-video-research-agent export search-hits --format csv
fencing-video-research-agent export search-hits --format json
```

### Validation Commands

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m mypy src
```

Architecture boundary scan:

```powershell
rg -n "googleapiclient|sqlalchemy|alembic|YOUTUBE_API_KEY|dotenv|os\.environ" src\fencing_video_research_agent\application src\fencing_video_research_agent\domain
```

### Current CLI Commands

```text
fencing-video-research-agent collect <query>
fencing-video-research-agent videos list
fencing-video-research-agent videos show <youtube_video_id>
fencing-video-research-agent runs list
fencing-video-research-agent runs show <run_id>
fencing-video-research-agent annotations show <youtube_video_id>
fencing-video-research-agent annotations set-status <youtube_video_id> <status>
fencing-video-research-agent annotations set-notes <youtube_video_id> --notes "..."
fencing-video-research-agent annotations set-label <youtube_video_id> <label>
fencing-video-research-agent annotations clear-label <youtube_video_id>
fencing-video-research-agent export videos
fencing-video-research-agent export search-hits
```

### Git Milestone Commits

Observed local milestone history:

```text
0b88aff Add search-hit provenance export
ca09fae Polish README and demo guide
3d88a03 Add research report through Milestone 8
46bdd09 Add pandas-backed video export workflow
b027a85 Add manual video annotation workflow
6c30c0d Add read-only collection run inspection commands
25d1598 Add read-only video inspection commands
b989403 Add CLI wiring for controlled YouTube collection
a969acf Add official YouTube Data API adapter
cc78e6e Add collection use case with fake gateway tests
91a6727 Add repository and Unit of Work persistence layer
6a29bfc Add database schema and Alembic foundation
a297736 Add domain and YouTube port foundation
31c5a46 Initialize fencing video research project
```

### Data Schema Summary

```text
videos
youtube_video_metadata
search_queries
collection_runs
search_hits
research_annotations
```

The most important provenance relationship is:

```text
search_queries -> collection_runs -> search_hits -> videos
```

### Manual Smoke-Test Procedure

1. Create a local `.env` from `.env.example`.
2. Put the real YouTube API key only in `.env`.
3. Run a small collection with `--max-results 5`.
4. Inspect the local SQLite database through read-only CLI commands.
5. Confirm that no API key, `.env` content, raw Google response, or stack trace is
   printed.

Local paths such as `data/fencing_video_research.db` are examples for the local
development workflow. The SQLite database is local research data and is ignored by
Git.
