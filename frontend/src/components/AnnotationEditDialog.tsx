import {
  Alert,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import type { SelectChangeEvent } from "@mui/material/Select";
import { useEffect, useState } from "react";

import type {
  ReviewStatus,
  UpdateVideoAnnotationRequest,
  VideoDetailResponse,
} from "../api/types";

type AnnotationEditDialogProps = {
  errorMessage: string | null;
  loading: boolean;
  onClose: () => void;
  onSave: (payload: UpdateVideoAnnotationRequest) => void;
  open: boolean;
  saving: boolean;
  video: VideoDetailResponse | null;
};

export function AnnotationEditDialog({
  errorMessage,
  loading,
  onClose,
  onSave,
  open,
  saving,
  video,
}: AnnotationEditDialogProps) {
  const [reviewStatus, setReviewStatus] = useState<ReviewStatus>("unreviewed");
  const [relevanceLabel, setRelevanceLabel] = useState("");
  const [notes, setNotes] = useState("");

  useEffect(() => {
    if (video === null) {
      return;
    }
    setReviewStatus(video.review_status ?? "unreviewed");
    setRelevanceLabel(video.relevance_label ?? "");
    setNotes(video.notes ?? "");
  }, [video]);

  function handleStatusChange(event: SelectChangeEvent<ReviewStatus>) {
    setReviewStatus(event.target.value as ReviewStatus);
  }

  function handleSave() {
    onSave({
      review_status: reviewStatus,
      relevance_label: relevanceLabel.trim() === "" ? null : relevanceLabel.trim(),
      notes: notes.trim() === "" ? null : notes,
    });
  }

  return (
    <Dialog fullWidth maxWidth="sm" onClose={saving ? undefined : onClose} open={open}>
      <DialogTitle>Edit annotation</DialogTitle>
      <DialogContent dividers>
        {loading ? (
          <Stack alignItems="center" minHeight={180} justifyContent="center" spacing={2}>
            <CircularProgress size={28} />
            <Typography color="text.secondary" variant="body2">
              Loading annotation
            </Typography>
          </Stack>
        ) : (
          <Stack spacing={2.5}>
            {errorMessage ? <Alert severity="error">{errorMessage}</Alert> : null}
            {video ? (
              <Typography color="text.secondary" variant="body2">
                {video.youtube_video_id}
              </Typography>
            ) : null}
            <FormControl fullWidth size="small">
              <InputLabel id="annotation-review-status-label">Review status</InputLabel>
              <Select
                label="Review status"
                labelId="annotation-review-status-label"
                onChange={handleStatusChange}
                value={reviewStatus}
              >
                <MenuItem value="unreviewed">unreviewed</MenuItem>
                <MenuItem value="reviewed">reviewed</MenuItem>
              </Select>
            </FormControl>
            <TextField
              fullWidth
              label="Relevance label"
              onChange={(event) => setRelevanceLabel(event.target.value)}
              size="small"
              value={relevanceLabel}
            />
            <TextField
              fullWidth
              label="Notes"
              minRows={4}
              multiline
              onChange={(event) => setNotes(event.target.value)}
              value={notes}
            />
          </Stack>
        )}
      </DialogContent>
      <DialogActions>
        <Button disabled={saving} onClick={onClose}>
          Cancel
        </Button>
        <Button
          disabled={loading || saving || video === null}
          onClick={handleSave}
          variant="contained"
        >
          {saving ? "Saving" : "Save"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
