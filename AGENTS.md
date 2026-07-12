# AGENTS.md

## 1. Purpose

This file defines the mandatory engineering rules for the Fencing Video Research Agent.

These instructions apply to every AI coding agent working in this repository.

Before modifying code, read:

1. `AGENTS.md`
2. `README.md`
3. `docs/project-brief.md`
4. Relevant source files
5. Relevant tests
6. Relevant architecture decision records

Do not invent requirements, files, commands, database fields, API behavior, or test
results.

When information is missing or contradictory, stop and ask for clarification.

---

## 2. Project objective

Build a reproducible Python application that:

1. Searches YouTube for public fencing videos.
2. Retrieves video metadata through the official YouTube Data API.
3. Stores videos, search queries, search hits, collection runs, and research
   annotations.
4. Preserves when and how each video was discovered.
5. Supports manual review.
6. Exports selected results to CSV and JSON.

The initial research focus is sabre fencing.

Phase 1 is a metadata collection and organization system. It is not a computer-vision
or video-analysis system.

---

## 3. Mandatory technology stack

Use the following technologies:

- Python 3.12
- YouTube Data API v3
- `google-api-python-client`
- SQLAlchemy 2.x
- Alembic
- SQLite
- pandas
- Typer
- Pydantic
- `pydantic-settings`
- pytest
- pytest-cov
- Ruff
- mypy
- `isodate`

Do not replace the language, database, ORM, migration framework, CLI framework, or
testing framework without explicit user approval.

Do not introduce another application framework, ORM, database, or programming language
without approval.

Use pandas for justified tabular processing and export operations.

Do not make domain models depend on pandas DataFrames.

---

## 4. Phase 1 boundaries

Do not implement the following unless explicitly requested:

- YouTube webpage scraping
- Video downloading
- Computer vision
- Video segmentation
- Scoring-action detection
- Event classification
- Model training
- Transcript extraction
- Web frontend
- Mobile application
- Cloud deployment
- Microservices
- Background task queues
- Distributed processing
- Authentication
- Multi-user support

Do not implement future phases merely because the architecture could support them.

---

## 5. Required architecture

Use a lightweight clean architecture.

### Domain

Contains fencing-research concepts and business rules.

Examples:

- Video
- Fencer
- Competition
- Search query
- Search hit
- Collection run
- Research annotation
- Review status

The domain must not import:

- SQLAlchemy
- Alembic
- Google API libraries
- Typer
- pandas
- SQLite-specific code
- Environment-variable libraries

The domain must not perform network, database, filesystem, or CLI operations.

### Application

Contains use cases and workflow orchestration.

Examples:

- Collect videos
- Refresh metadata
- Review a video
- List stored videos
- Export results
- View collection history

The application layer may depend on domain models and ports.

It must not contain:

- Raw SQL
- SQLAlchemy session construction
- Google API client construction
- Typer presentation logic
- SQLite-specific logic
- Raw Google API response dictionaries

### Ports

Ports are typed interfaces for external capabilities.

Examples:

- YouTube gateway
- Video repository
- Collection-run repository
- Annotation repository
- Unit of work
- Export writer
- Clock

Create ports only for meaningful external boundaries or replacement points.

Do not create an interface for every class.

### Infrastructure

Contains concrete technical implementations.

Examples:

- YouTube API adapter
- SQLAlchemy mappings
- SQLAlchemy repositories
- SQLite configuration
- Alembic migrations
- CSV and JSON writers
- pandas-based export processing
- Logging configuration

Infrastructure may implement application ports.

Domain and application code must not depend on infrastructure implementations.

### Interface

The Phase 1 interface is a Typer command-line application.

The CLI may:

- Parse arguments
- Display messages
- Select exit codes
- Call application use cases

The CLI must not contain business rules, raw SQL, database session construction, or
direct YouTube API calls.

### Composition root

Create one clear bootstrap location where settings, adapters, repositories, use cases,
and CLI dependencies are connected.

Do not scatter dependency construction across unrelated modules.

---

## 6. Data and database rules

Use SQLAlchemy 2.x-style APIs.

Use Alembic for persistent schema changes.

After migrations are introduced, do not use `create_all()` as the normal schema
migration strategy.

Required data-integrity rules:

- YouTube video IDs must be unique.
- Repeated collection must not create duplicate videos.
- One video may be linked to multiple search queries.
- Every search-to-video relationship must be preserved.
- YouTube metadata must be stored separately from researcher annotations.
- Metadata refresh must not overwrite researcher annotations.
- Store timestamps in UTC.
- Record first-seen and last-refreshed timestamps.
- Use transactions for multi-step writes.
- Roll back failed transactions.
- Represent missing optional metadata explicitly.
- Do not silently discard incomplete records.
- Avoid N+1 database queries.
- Use database constraints for critical integrity rules.

Every schema change requires:

1. Updated SQLAlchemy models
2. An Alembic migration
3. Relevant tests
4. Updated data documentation
5. A compatibility and rollback explanation

Do not edit an already-applied migration. Create a new migration.

---

## 7. YouTube API rules

Use only the official YouTube Data API.

Use:

- `search.list` for discovery
- `videos.list` for metadata enrichment

The YouTube adapter must:

- Handle pagination explicitly.
- Record search queries and relevant parameters.
- Deduplicate video IDs before enrichment.
- Batch metadata requests where supported.
- Handle missing optional fields.
- Distinguish transient failures from permanent failures.
- Use capped retries with backoff only for appropriate transient failures.
- Never use unlimited retries.
- Never log or expose the API key.
- Convert Google responses into project-owned types at the adapter boundary.

Do not allow raw Google response dictionaries to spread through the application.

Verify version-sensitive API behavior against official documentation.

---

## 8. Configuration and secrets

Use one centralized settings component.

Use environment variables for secrets and machine-specific configuration.

The real `.env` file must never be committed.

`.env.example` must contain placeholders only.

Never:

- Hardcode an API key
- Print an API key
- Log an API key
- Place real credentials in tests
- Include secrets in errors
- Store secrets in documentation

The application must fail early with a clear, sanitized message when required
configuration is missing or invalid.

---

## 9. Testing rules

Normal automated tests must not call the live YouTube API.

Tests must be deterministic and runnable without internet access.

Use:

- Fake ports
- Mocked API clients
- Fabricated API responses
- Temporary SQLite databases
- Temporary filesystem directories
- Fixed clocks where time affects behavior

A live API smoke test may exist only if it:

- Is excluded from the default test suite
- Requires an explicit marker or environment flag
- Uses minimal quota
- Never runs automatically
- Never exposes credentials

Required test coverage includes:

- Duplicate video IDs
- Idempotent repeated collection
- One video discovered by multiple queries
- Missing optional metadata
- Empty API results
- Pagination
- Transient and permanent API failures
- Invalid or missing configuration
- Database constraint failures
- Transaction rollback
- Annotation preservation during refresh
- CSV and JSON export correctness
- Database migrations

Every bug fix must include a regression test when practical.

Do not delete, weaken, or skip an existing test merely to make new code pass.

If an existing test is incorrect, explain why before changing its expected behavior.

---

## 10. Change-safety rules

Before changing existing behavior:

1. Inspect the relevant implementation.
2. Inspect relevant tests.
3. State the requested behavior.
4. Identify affected contracts.
5. Identify regression risks.
6. Propose the smallest coherent change.
7. List the files expected to change.

For large, destructive, ambiguous, or architectural changes, stop after the plan and
request approval.

Approval is required for:

- Framework changes
- Changing the primary database engine or persistence architecture
- ORM changes
- Schema redesign
- Architecture-boundary changes
- Breaking CLI changes
- Public interface changes
- Dependency replacement
- Broad refactoring
- Concurrency
- Caching
- Removal of existing functionality
- Destructive migrations

While coding:

- Make the smallest coherent change.
- Do not modify unrelated files.
- Do not combine a feature with unrelated refactoring.
- Preserve existing behavior unless a change was requested.
- Add tests with the implementation.
- Do not hide failures with fallbacks.
- Do not disable tests, linting, or type checking to make checks pass.
- Do not use `# type: ignore`, `noqa`, or test skips without a specific explanation.
- Do not rewrite Git history.
- Do not force-push.
- Do not delete user data.
- Do not silently change defaults, configuration names, CLI commands, database fields,
  or export columns.

When unexpected behavior appears, stop and report it instead of guessing.

---

## 11. Performance rules

Performance changes must be based on an observed or credible bottleneck.

Required practices:

- Batch YouTube metadata requests where supported.
- Deduplicate IDs before API enrichment.
- Avoid duplicate network calls during one collection run.
- Avoid N+1 database queries.
- Use pagination for potentially large result sets.
- Avoid loading unbounded datasets into memory.
- Use chunking for large exports when necessary.
- Avoid unnecessary database commits.
- Avoid unnecessary disk writes.
- Use pandas only where tabular processing provides a clear benefit.
- Add database indexes only for actual or clearly justified query patterns.
- Cap retries and backoff duration.

Do not introduce the following without a demonstrated need and explicit approval:

- Async programming
- Threads
- Multiprocessing
- Caching
- Background queues
- Distributed systems
- Microservices

Do not sacrifice correctness, data integrity, security, reproducibility, or
maintainability for speculative performance improvements.

For a performance optimization, report:

1. The bottleneck
2. How it was measured or estimated
3. The proposed change
4. Expected benefit
5. Complexity and correctness risks
6. Before-and-after evidence when practical

---

## 12. Coding standards

Use Python 3.12-compatible syntax.

Required practices:

- Explicit type hints for public functions
- Clear return types
- Small, focused functions
- Clear names
- Limited side effects
- UTC-aware datetimes
- Context managers for managed resources
- Typed exceptions for meaningful failure categories
- Useful but bounded logging
- Docstrings for public modules, classes, and non-obvious behavior
- Comments that explain why, not obvious syntax

Avoid:

- Global mutable state
- Hidden singleton services
- Circular imports
- Silent exception swallowing
- Unbounded loops
- Unbounded retries
- Very large service classes
- Deep inheritance hierarchies
- Duplicate business rules
- Magic strings spread across files
- Premature abstraction
- Premature optimization
- Dead code
- Placeholder production logic presented as complete

Use Pydantic for settings and external-boundary validation.

Prefer plain Python types for domain models.

---

## 13. Dependency rules

Declare all dependencies in `pyproject.toml`.

Do not install an undeclared production dependency.

Before adding a dependency, explain:

1. What problem it solves
2. Why the standard library is insufficient
3. Why existing dependencies are insufficient
4. Maintenance and security implications
5. Alternatives considered

Do not add overlapping libraries that solve the same problem without justification.

Do not replace an approved dependency without explicit approval.

---

## 14. Documentation and decisions

Update documentation when behavior, setup, data, architecture, or commands change.

Use `docs/decisions/` for important Architecture Decision Records.

An ADR is required for decisions involving:

- Architecture boundaries
- Database strategy
- External services
- Public interfaces
- Major dependencies
- Performance architecture
- Security architecture
- Data compatibility
- Deployment

Do not create an ADR for routine implementation details.

Do not document behavior that is not implemented.

---

## 15. Validation

During development, run targeted checks for the component being changed.

Before completing a code change, run:

```powershell
python -m pytest
python -m ruff check .
python -m mypy src
```

Run formatting validation when formatting is configured:

```powershell
python -m ruff format --check .
```

Documentation-only changes do not require the full Python test suite unless they alter
commands, configuration, or executable examples.

For database changes, validate migrations on:

- A clean temporary database
- A database representing the previous schema when applicable

Do not claim that a command passed unless it was actually executed successfully.

If a command cannot be run, explain why.

---

## 16. Completion report

After a code change, provide a concise report containing the following sections.

### Summary

What changed.

### Files changed

Files created, modified, moved, or deleted.

### Reasoning

Why this approach was selected and which meaningful alternatives were rejected.

### Compatibility

Effects on existing behavior, CLI commands, configuration, database schema, and
exports.

### Performance and security

Relevant performance, secret-handling, logging, or data-access effects.

### Validation

Commands actually executed and their results.

### Limitations

Known limitations or remaining uncertainty.

### Rollback

How the change can be reverted safely.

Do not produce a long report for a documentation-only or trivial change unless the
user requests one.

---

## 17. Evidence and hallucination rules

Clearly distinguish between:

- Facts observed in the repository
- Requirements documented in the repository
- Requirements from the current user request
- Assumptions
- Recommendations
- Unverified possibilities

Never claim:

- A file exists without inspecting it
- A command succeeded without seeing its result
- Tests passed without running them
- An API field exists without verifying it
- A database field exists without inspecting the schema
- A library supports behavior without evidence
- A requirement exists when it is not documented

When repository documents conflict:

1. Identify the conflict.
2. Stop the affected work.
3. Ask which source is authoritative.

When technical behavior is unfamiliar or version-sensitive, verify it using official
documentation.

---

## 18. Definition of done

A code task is complete only when:

- The requested behavior is implemented.
- Existing behavior is preserved unless intentionally changed.
- Architecture boundaries are respected.
- Relevant tests are present.
- Targeted tests pass.
- The full test suite passes, or failures are reported honestly.
- Ruff passes.
- mypy passes.
- Migrations are valid when applicable.
- Documentation is updated when necessary.
- No secrets are exposed.
- No unrelated files are changed.
- Performance and compatibility effects are considered.
- The final diff has been reviewed.
- A concise completion report is provided.
