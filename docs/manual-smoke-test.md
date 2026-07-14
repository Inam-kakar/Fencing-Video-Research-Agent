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

## Keep The Smoke Test Small

For early project validation, do not raise `--max-results` above `5` unless you have a
specific reason. Larger searches consume more quota and create more local data to
review.
