import { Alert, Button, Stack, TextField } from "@mui/material";
import type { FormEvent } from "react";
import { useCallback, useEffect, useState } from "react";

import { getVideos } from "../api/client";
import type { VideoListResponse } from "../api/types";
import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { PageHeader } from "../components/PageHeader";
import { VideosTable } from "../components/VideosTable";

const PAGE_LIMIT = 50;

type VideosState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; videos: VideoListResponse };

export function VideosPage() {
  const [videosState, setVideosState] = useState<VideosState>({ status: "loading" });
  const [searchInput, setSearchInput] = useState("");
  const [appliedSearch, setAppliedSearch] = useState("");

  const loadVideos = useCallback(() => {
    setVideosState({ status: "loading" });
    getVideos({
      limit: PAGE_LIMIT,
      offset: 0,
      search: appliedSearch,
    })
      .then((videos) => {
        setVideosState({ status: "ready", videos });
      })
      .catch((error: unknown) => {
        const message = error instanceof Error ? error.message : "Unable to load stored videos";
        setVideosState({ status: "error", message });
      });
  }, [appliedSearch]);

  useEffect(() => {
    loadVideos();
  }, [loadVideos]);

  function handleSearchSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAppliedSearch(searchInput.trim());
  }

  return (
    <Stack spacing={3}>
      <PageHeader
        description="Browse stored video metadata from the local read-only API."
        title="Stored Videos"
      />
      <Stack
        alignItems={{ xs: "stretch", sm: "flex-end" }}
        component="form"
        direction={{ xs: "column", sm: "row" }}
        onSubmit={handleSearchSubmit}
        spacing={2}
      >
        <TextField
          fullWidth
          label="Search videos"
          onChange={(event) => setSearchInput(event.target.value)}
          size="small"
          value={searchInput}
        />
        <Button type="submit" variant="contained">
          Search
        </Button>
      </Stack>
      <Alert severity="info">
        Showing up to {PAGE_LIMIT} stored videos from the current API query.
      </Alert>
      {videosState.status === "loading" ? <LoadingState /> : null}
      {videosState.status === "error" ? (
        <ErrorState message={videosState.message} onRetry={loadVideos} />
      ) : null}
      {videosState.status === "ready" ? <VideosTable videos={videosState.videos.items} /> : null}
    </Stack>
  );
}
