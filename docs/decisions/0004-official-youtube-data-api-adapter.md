# ADR-0004: Official YouTube Data API adapter

## Status

Accepted

## Context

The project is a Phase 1 research application for reproducible public fencing-video
metadata collection. Earlier milestones established framework-free domain models,
project-owned YouTube gateway contracts, SQLAlchemy persistence, repository and Unit
of Work boundaries, and an application-layer collection use case.

The project instructions require official YouTube Data API v3 usage, secret-safe API
key handling, offline deterministic tests, and strict clean-architecture boundaries.
The application layer must not depend on Google API libraries or raw Google response
dictionaries.

## Decision

Implement the concrete YouTube gateway in the infrastructure layer using the official
YouTube Data API v3. The adapter uses `search.list` for discovery and `videos.list`
for metadata enrichment. Raw Google response dictionaries are converted inside the
adapter into project-owned `YouTubeSearchResult` and `YouTubeMetadata` objects.

Add centralized infrastructure settings with `pydantic-settings` and store the
YouTube API key as a secret value. The Google API client is created with
`googleapiclient.discovery.build("youtube", "v3", developerKey=..., cache_discovery=False)`.

The adapter accepts an injected Google client so tests can use fake clients and avoid
live API calls. It also accepts an injected clock for deterministic metadata refresh
timestamps and an injected sleep function so retry tests do not wait.

## Reasons

The official API is required by the project instructions and provides stable,
quota-governed metadata access. Scraping YouTube webpages is explicitly out of scope
and would be less reproducible, more brittle, and more likely to violate project
boundaries.

Keeping the adapter in infrastructure preserves the dependency direction: domain and
application code depend on project-owned models and ports, while Google-specific
client construction and raw dictionaries remain isolated.

## API Key Protection

The API key is loaded from `YOUTUBE_API_KEY` through centralized settings and stored
as a secret value. Missing or blank keys raise sanitized configuration errors. The
adapter and settings code do not print, log, or include the key in exception messages.

Tests use placeholder environment values or injected fake clients. Normal automated
tests do not require or read a real API key.

## API Usage

Discovery uses `search.list` with `part=snippet`, `type=video`, the request query,
and a small allowlist of supported search parameters. Adapter-controlled fields such
as `part`, `q`, `type`, `maxResults`, and `pageToken` cannot be overridden.

Metadata enrichment uses `videos.list` with `part=snippet,contentDetails,statistics`.
Requested video IDs are deduplicated and batched before requests.

## Error Handling

Transient YouTube API errors, such as retryable server failures and rate limiting,
are retried with a small capped retry loop. Quota exhaustion is treated as
non-retryable for the current run to avoid wasting quota. Permanent request or
configuration failures are raised as permanent gateway errors with sanitized messages.

## Trade-offs

The adapter supports a deliberate search-parameter allowlist instead of forwarding
arbitrary API parameters. This reduces flexibility, but improves reproducibility and
prevents callers from bypassing adapter-controlled behavior.

The milestone does not add live smoke tests. This keeps the default suite offline and
deterministic, but means API credentials and quota behavior still need manual or
explicitly marked validation in a later milestone if desired.

## Not Implemented Yet

This milestone does not add CLI commands, composition-root wiring, live YouTube smoke
tests, exports, pandas export logic, video downloading, computer vision, event or
scoring detection, web UI, cloud deployment, database schema changes, or Alembic
migrations.

## Security Impact

No real secrets are committed. The adapter uses injected clients in tests, sanitized
errors, and secret-aware settings to reduce accidental credential exposure.

## Migration And Compatibility

No database schema or persistent data migration is introduced. The existing
`YouTubeGateway` port and application collection use case remain unchanged.

## Reversibility

Before CLI/composition wiring depends on this adapter, the infrastructure adapter and
settings files can be removed without changing domain, application, or persistence
contracts. After wiring is added, changes should preserve the `YouTubeGateway`
contract or be handled through a follow-up ADR.
