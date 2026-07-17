# Frontend Demo

This document describes the local demo workflow for the React, TypeScript, Vite, and
MUI frontend dashboard.

The frontend calls only the local FastAPI API. It does not call YouTube, does not
connect to SQLite directly, and must not receive `YOUTUBE_API_KEY`.

## 1. Start the FastAPI API

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn fencing_video_research_agent.api.main:create_app --factory --reload
```

By default, the API runs at:

```text
http://localhost:8000
```

## 2. Install Frontend Dependencies

From the repository root:

```powershell
cd frontend
npm install
```

## 3. Start the Frontend

From `frontend/`:

```powershell
npm run dev
```

The Vite development server uses:

```text
http://localhost:5173
```

## 4. Open the Browser

Open the Vite local URL shown in the terminal. Confirm that:

- The app shell and dashboard title appear.
- The API health chip appears.
- Summary metric cards appear.
- The Dashboard tab loads.
- The Videos tab loads a read-only stored-video table or a readable empty state.
- The Collection Runs tab loads a read-only collection-run table or a readable empty
  state.
- The Search Hits tab loads a read-only provenance table or a readable empty state.
- API errors show safe messages.
- YouTube links are shown as links when video URLs are available.
- The Videos tab provides an edit action for stored-video annotation fields.
- The annotation dialog loads the current video annotation.
- Changing `review_status`, `relevance_label`, or `notes` and saving updates the
  table after the dialog closes.
- Refreshing the browser preserves the saved annotation values.
- The Videos tab provides a controlled metadata collection panel.
- Searching locally for `Sandro Bazadze fencing sabre` shows any matching stored
  records, or a readable empty state if none are stored yet.
- Collecting metadata for `Sandro Bazadze fencing sabre` with a small `max_results`
  value stores videos through the backend and refreshes the Videos table.
- The Collection Runs tab shows the new collection run after collection.
- The Search Hits tab shows the new provenance rows after collection.
- No edit controls are present on the Collection Runs tab.
- No edit controls are present on the Search Hits tab.
- No export buttons are present.

## Configuration

The frontend API base URL can be configured with:

```text
VITE_API_BASE_URL=http://localhost:8000
```

Do not put backend secrets in frontend configuration. In particular, do not place
`YOUTUBE_API_KEY` in any frontend environment file.

## Browser Metadata Collection Demo

Use this only when the backend `.env` has a valid `YOUTUBE_API_KEY`.

1. Start FastAPI on a local port:

   ```powershell
   .\.venv\Scripts\python.exe -m uvicorn fencing_video_research_agent.api.main:create_app --factory --reload --host 127.0.0.1 --port 8001
   ```

2. Start Vite with the matching API URL:

   ```powershell
   cd frontend
   $env:VITE_API_BASE_URL="http://127.0.0.1:8001"
   npm run dev -- --host localhost --port 5173 --strictPort
   ```

3. Open the frontend and search local videos for:

   ```text
   Sandro Bazadze fencing sabre
   ```

4. If no local records appear, use the Videos tab collection panel with `max_results`
   set to `5` or `10`.
5. Confirm a success message appears.
6. Confirm the Videos table shows stored results.
7. Confirm the Collection Runs tab shows the new run.
8. Confirm the Search Hits tab shows provenance rows.
9. Confirm the frontend never asks for or displays `YOUTUBE_API_KEY`.
10. Confirm no video downloading, computer vision, scoring detection, event detection,
    or model-training UI exists.

## Annotation Editing Scope

Browser annotation editing is intentionally limited to already stored videos and only
these fields:

- `review_status`
- `relevance_label`
- `notes`

The frontend must not edit YouTube metadata, collection runs, search hits, export
files, richer annotation fields, or arbitrary collection/search parameters.

## Browser Collection Scope

Browser collection is intentionally limited to:

- `query`
- `max_results`

The frontend must not send arbitrary YouTube API parameters, receive
`YOUTUBE_API_KEY`, call YouTube directly, read SQLite, read backend `.env` files, run
shell commands, or start exports.
