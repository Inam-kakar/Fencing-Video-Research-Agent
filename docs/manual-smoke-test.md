# Manual Smoke Test

This project keeps normal automated tests offline and deterministic. Use this manual
procedure only when you intentionally want to spend a small amount of YouTube Data API
quota against a local SQLite database.

## Prepare Local Configuration

Create a local `.env` file from `.env.example` and put the real API key only in
`.env`:

```text
YOUTUBE_API_KEY=your_real_key_here
DATABASE_URL=sqlite:///data/fencing_video_research.db
LOG_LEVEL=INFO
```

Do not commit `.env`. Do not paste the real key into chat, GitHub issues, terminal
screenshots, or documentation.

## Run One Small Collection

Use a small query and keep the first smoke test capped at five results:

```powershell
fencing-video-research-agent collect "sabre fencing final" --max-results 5
```

Expected safe output includes counts such as requested max results, search results
returned, unique videos, stored or updated videos, search hits recorded, and duplicate
search results skipped.

The output must not include the API key, `.env` contents, raw Google API responses,
or a stack trace.

## Verify The Local SQLite Database

After a successful run, the default SQLite file should exist at:

```text
data/fencing_video_research.db
```

The CLI runs Alembic migrations before collection, so the database should contain the
Phase 1 metadata tables such as `videos`, `search_queries`, `collection_runs`,
`search_hits`, and `youtube_video_metadata`.

## Inspect Stored Videos

After collection, inspect the stored video records without calling YouTube again:

```powershell
fencing-video-research-agent videos list
```

Show one stored video by YouTube video ID:

```powershell
fencing-video-research-agent videos show <youtube_video_id>
```

These read-only commands run Alembic migrations before reading, but they do not
collect new metadata and do not require `YOUTUBE_API_KEY`.

## Inspect Collection Runs

Review previous collection runs without calling YouTube again:

```powershell
fencing-video-research-agent runs list
```

Show the query, parameters, timing, and returned videos for one stored run:

```powershell
fencing-video-research-agent runs show <run_id>
```

These read-only commands use the local database only. They do not collect new
metadata, refresh stored metadata, or require `YOUTUBE_API_KEY`.

## Review And Annotate Stored Videos

Manual annotation commands use only the local database. They run Alembic migration
checks before reading or writing, but they do not call YouTube and do not require
`YOUTUBE_API_KEY`.

Show the annotation state for one stored video:

```powershell
fencing-video-research-agent annotations show <youtube_video_id>
```

Create or update the manual review status:

```powershell
fencing-video-research-agent annotations set-status <youtube_video_id> reviewed
```

The only valid review status values are `unreviewed` and `reviewed`.

Create or update researcher notes without echoing long notes back to the terminal:

```powershell
fencing-video-research-agent annotations set-notes <youtube_video_id> --notes "Good sabre footwork example."
```

Set or clear the single relevance label stored in `research_annotations.relevance_label`:

```powershell
fencing-video-research-agent annotations set-label <youtube_video_id> relevant
fencing-video-research-agent annotations clear-label <youtube_video_id>
```

The current schema supports one relevance label per video. It does not support true
multi-label annotation yet.

## Export Stored Videos

Export stored video metadata, compact collection provenance, and manual annotation
fields without calling YouTube again:

```powershell
fencing-video-research-agent export videos
```

By default this writes CSV output to:

```text
data/exports/videos.csv
```

Export JSON instead:

```powershell
fencing-video-research-agent export videos --format json
```

Use a custom path when needed:

```powershell
fencing-video-research-agent export videos --output data/exports/my-videos.csv
```

Existing files are not overwritten unless explicitly requested:

```powershell
fencing-video-research-agent export videos --overwrite
```

Export one row per search hit for provenance auditing:

```powershell
fencing-video-research-agent export search-hits
```

By default this writes CSV output to:

```text
data/exports/search_hits.csv
```

Export JSON search-hit provenance instead:

```powershell
fencing-video-research-agent export search-hits --format json
```

Export commands use the local database only. They run Alembic migration checks before
reading, do not collect or refresh metadata, and do not require `YOUTUBE_API_KEY`.
Generated files under `data/exports/` are ignored by Git.

## Keep The Smoke Test Small

For early project validation, do not raise `--max-results` above `5` unless you have a
specific reason. Larger searches consume more quota and create more local data to
review.
