# ADR-0003: Repository and Unit of Work boundaries

## Status

Accepted

## Context

Milestone 1 established framework-free domain models and project-owned YouTube port
types. Milestone 2A added SQLAlchemy mappings, SQLite support, Alembic migrations, and
the Phase 1 persistence schema.

The application now needs a persistence boundary that future use cases can call
without depending on SQLAlchemy sessions, ORM classes, raw SQL, or database-specific
details. The project instructions require transactions for multi-step writes,
rollback on failed transactions, duplicate YouTube IDs to reuse one video row, search
provenance preservation, and annotations to remain separate from YouTube metadata.

## Decision

Add repository ports for videos, collection provenance, and annotations. Add a Unit of
Work port for explicit transaction boundaries. Implement these ports with SQLAlchemy
inside the infrastructure layer.

Repository ports expose domain models and lightweight `NewType` persistence handles:

- `VideoRecordId`
- `SearchQueryRecordId`
- `CollectionRunRecordId`

These handles live in the ports layer. They are not domain identities and they do not
expose SQLAlchemy models or sessions.

The SQLAlchemy Unit of Work opens one session on entry, commits only when `commit()`
is called, rolls back on exception, rolls back when exiting without a commit, and
always closes the session.

## Alternatives considered

- Expose raw integer database IDs in repository ports.
- Expose SQLAlchemy ORM objects to application code.
- Create generic repositories for every table.
- Delay Unit of Work until application use cases are implemented.
- Hide all persistence handles and make one broad collection method now.

## Reasons for rejection

Raw integers are easy to mix up across tables and make repository calls look more
database-shaped than necessary. Exposing ORM objects would leak infrastructure into
the application layer. Generic repositories would add abstraction without matching
Phase 1 workflows. Delaying Unit of Work would postpone required transaction behavior.
A broad collection method would pre-implement application orchestration before those
use cases are approved.

## Consequences

Future application use cases can coordinate persistence with a small number of
repositories and an explicit Unit of Work while keeping the domain framework-free.

The ports still expose persistence handles for multi-step workflows, such as adding a
collection run and then adding its search hits. This is a pragmatic compromise:
handles remain typed and port-level, but they are not pure domain concepts.

## Performance impact

Repositories use indexed lookup paths from the schema: YouTube video ID, query text
plus parameter fingerprint, collection-run ID, and video ID. Search parameter
fingerprints avoid querying JSON contents for identity. No caching, concurrency, or
background work is introduced.

## Security impact

No secrets are introduced, read, printed, or logged. Repository methods accept optional
collection-run error messages; future application code must keep those sanitized and
must never store API keys or credentials.

## Migration and compatibility

No schema migration is introduced in this milestone. The repositories use the schema
created by Alembic revision `0001`.

The boundary remains compatible with future PostgreSQL migration because application
code sees ports and domain models rather than SQLite-specific SQLAlchemy details.

## Reversibility

The repository and Unit of Work layer can be removed or revised before application use
cases depend on it. Once use cases call these ports, changes should be made through
small compatibility-preserving revisions or a follow-up ADR.

