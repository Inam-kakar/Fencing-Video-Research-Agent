import { Alert, Button, Snackbar, Stack, TextField } from "@mui/material";
import type { FormEvent } from "react";
import { useCallback, useEffect, useState } from "react";

import { getVideo, getVideos, updateVideoAnnotation } from "../api/client";
import type {
  CollectionRunCreateResponse,
  UpdateVideoAnnotationRequest,
  VideoDetailResponse,
  VideoListItemResponse,
  VideoListResponse,
} from "../api/types";
import { AnnotationEditDialog } from "../components/AnnotationEditDialog";
import { CollectionRunForm } from "../components/CollectionRunForm";
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
  const [selectedVideo, setSelectedVideo] = useState<VideoDetailResponse | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [dialogLoading, setDialogLoading] = useState(false);
  const [dialogSaving, setDialogSaving] = useState(false);
  const [dialogError, setDialogError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

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

  function handleEditAnnotation(video: VideoListItemResponse) {
    setDialogOpen(true);
    setSelectedVideo(null);
    setDialogError(null);
    setDialogLoading(true);

    getVideo(video.youtube_video_id)
      .then((videoDetail) => {
        setSelectedVideo(videoDetail);
      })
      .catch((error: unknown) => {
        const message =
          error instanceof Error ? error.message : "Unable to load annotation details";
        setDialogError(message);
      })
      .finally(() => {
        setDialogLoading(false);
      });
  }

  function handleDialogClose() {
    if (dialogSaving) {
      return;
    }
    setDialogOpen(false);
    setSelectedVideo(null);
    setDialogError(null);
  }

  function handleAnnotationSave(payload: UpdateVideoAnnotationRequest) {
    if (selectedVideo === null) {
      return;
    }

    setDialogSaving(true);
    setDialogError(null);
    updateVideoAnnotation(selectedVideo.youtube_video_id, payload)
      .then(() => {
        setDialogOpen(false);
        setSelectedVideo(null);
        setSuccessMessage("Annotation updated.");
        loadVideos();
      })
      .catch((error: unknown) => {
        const message = error instanceof Error ? error.message : "Unable to update annotation";
        setDialogError(message);
      })
      .finally(() => {
        setDialogSaving(false);
      });
  }

  function handleCollectionCreated(result: CollectionRunCreateResponse) {
    setSearchInput(result.query);
    setAppliedSearch(result.query);
    setSuccessMessage(
      `Collection completed: ${result.videos_stored} videos stored and ${result.search_hits_recorded} search hits recorded.`,
    );
    if (appliedSearch === result.query) {
      loadVideos();
    }
  }

  const showNoLocalResults =
    videosState.status === "ready" &&
    videosState.videos.items.length === 0 &&
    appliedSearch.trim() !== "";

  return (
    <Stack spacing={3}>
      <PageHeader
        description="Browse stored video metadata and collect controlled YouTube metadata through the backend."
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
      {showNoLocalResults ? (
        <Alert severity="warning">No stored videos found for this search.</Alert>
      ) : null}
      <CollectionRunForm
        initialQuery={appliedSearch || searchInput}
        onCollected={handleCollectionCreated}
      />
      {videosState.status === "loading" ? <LoadingState /> : null}
      {videosState.status === "error" ? (
        <ErrorState message={videosState.message} onRetry={loadVideos} />
      ) : null}
      {videosState.status === "ready" ? (
        <VideosTable
          onEditAnnotation={handleEditAnnotation}
          videos={videosState.videos.items}
        />
      ) : null}
      <AnnotationEditDialog
        errorMessage={dialogError}
        loading={dialogLoading}
        onClose={handleDialogClose}
        onSave={handleAnnotationSave}
        open={dialogOpen}
        saving={dialogSaving}
        video={selectedVideo}
      />
      <Snackbar
        autoHideDuration={3000}
        onClose={() => setSuccessMessage(null)}
        open={successMessage !== null}
      >
        <Alert
          onClose={() => setSuccessMessage(null)}
          severity="success"
          variant="filled"
        >
          {successMessage}
        </Alert>
      </Snackbar>
    </Stack>
  );
}
