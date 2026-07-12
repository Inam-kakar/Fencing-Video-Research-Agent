# ADR-0001: Lightweight clean architecture foundation

## Status

Accepted

## Context

The project is a Phase 1 research application for discovering, collecting, reviewing,
and exporting public fencing-video metadata through the official YouTube Data API.
The repository currently contains only a package scaffold, documentation, dependency
configuration, and an import test.

Project instructions require a lightweight clean architecture with framework-free
domain models, application-level use cases, typed ports for external boundaries, and
infrastructure adapters for Google APIs, SQLAlchemy, SQLite, files, and exports.
Phase 1 must not include future video-analysis features, live API calls in normal
tests, or raw Google response dictionaries outside the adapter boundary.

## Decision

Establish the first architecture foundation with:

- a `domain` package for plain Python research concepts and business rules;
- a `ports` package for project-owned external contracts;
- project-owned YouTube search and metadata types at the port boundary;
- deterministic tests that use only local objects and fakes.

Domain models will not import SQLAlchemy, Alembic, Typer, pandas, Google libraries,
SQLite-specific code, or environment-variable libraries. YouTube ports will expose
typed request/result objects and gateway errors rather than raw API dictionaries.

Milestone 1 deliberately excludes persistence, migrations, concrete adapters, CLI
commands, exports, and dependency wiring.

## Alternatives considered

- Build a single script that searches YouTube and writes files immediately.
- Start with SQLAlchemy models and derive domain behavior from ORM classes.
- Add all planned packages and empty modules up front.
- Delay all architecture structure until the first concrete use case.

## Reasons for rejection

A single script would mix CLI, API, persistence, and business rules in a way that
conflicts with the project instructions. ORM-first modeling would make the domain
depend on SQLAlchemy too early. Creating empty layers up front would add noise without
tested behavior. Delaying all structure would make it easier for raw API payloads or
framework concerns to spread into the core application.

## Consequences

The project gains a small, tested foundation for future use cases. Later milestones
can add repositories, Alembic migrations, a concrete YouTube adapter, Typer commands,
and export writers behind existing boundaries.

The initial foundation does not yet provide a runnable CLI, database schema, or API
adapter. Those must be added in later milestones with their own tests and, where
appropriate, additional ADRs.

## Performance impact

There is no meaningful runtime performance impact in this milestone because no I/O,
database access, network access, or export processing is introduced. The port design
keeps future batching and pagination decisions inside the YouTube adapter and
application use cases.

## Security impact

No secrets are introduced, read, logged, printed, or stored. The YouTube API key will
remain an infrastructure configuration concern in a later milestone. Raw Google
responses are kept out of domain and application contracts by introducing
project-owned port types.

## Migration and compatibility

No database schema or persistent data migration is introduced. Existing imports remain
compatible because the package root is unchanged. Future schema work should add
SQLAlchemy models, Alembic migration files, data documentation, and migration tests.

## Reversibility

This decision can be reversed by removing the new domain and port packages before they
are used by later application code. After later milestones depend on these contracts,
changes should be made through small compatibility-preserving refactors or dedicated
ADRs for boundary changes.

