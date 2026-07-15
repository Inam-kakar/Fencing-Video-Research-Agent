# Frontend Demo

This document describes the local demo workflow for the React, TypeScript, Vite, and
MUI frontend dashboard.

The frontend reads only from the local read-only FastAPI API. It does not call
YouTube, does not connect to SQLite directly, and must not receive `YOUTUBE_API_KEY`.

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
- No annotation editing controls, export buttons, or collection UI are present.

## Configuration

The frontend API base URL can be configured with:

```text
VITE_API_BASE_URL=http://localhost:8000
```

Do not put backend secrets in frontend configuration. In particular, do not place
`YOUTUBE_API_KEY` in any frontend environment file.
