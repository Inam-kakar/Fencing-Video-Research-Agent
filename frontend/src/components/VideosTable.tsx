import {
  Chip,
  Link,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from "@mui/material";

import type { VideoListItemResponse } from "../api/types";
import { DataTableEmptyState } from "./DataTableEmptyState";

type VideosTableProps = {
  videos: VideoListItemResponse[];
};

export function VideosTable({ videos }: VideosTableProps) {
  if (videos.length === 0) {
    return <DataTableEmptyState message="No stored videos found." />;
  }

  return (
    <TableContainer component={Paper}>
      <Table aria-label="Stored videos table" size="small">
        <TableHead>
          <TableRow>
            <TableCell>YouTube ID</TableCell>
            <TableCell>Title</TableCell>
            <TableCell>Channel</TableCell>
            <TableCell align="right">Duration</TableCell>
            <TableCell>Published</TableCell>
            <TableCell align="right">Views</TableCell>
            <TableCell>Review status</TableCell>
            <TableCell>Relevance label</TableCell>
            <TableCell>YouTube link</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {videos.map((video) => (
            <TableRow key={video.youtube_video_id}>
              <TableCell>{video.youtube_video_id}</TableCell>
              <TableCell sx={{ minWidth: 260 }}>{video.title}</TableCell>
              <TableCell>{video.channel_title}</TableCell>
              <TableCell align="right">{formatDuration(video.duration_seconds)}</TableCell>
              <TableCell>{formatDate(video.published_at)}</TableCell>
              <TableCell align="right">{formatNumber(video.view_count)}</TableCell>
              <TableCell>
                <Chip label={video.review_status ?? "unreviewed"} size="small" />
              </TableCell>
              <TableCell>{video.relevance_label ?? "Not labeled"}</TableCell>
              <TableCell>
                {video.video_url ? (
                  <Link href={video.video_url} rel="noreferrer" target="_blank">
                    Open
                  </Link>
                ) : (
                  "Not available"
                )}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}

function formatDuration(seconds: number | null): string {
  if (seconds === null) {
    return "Not recorded";
  }
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}:${String(remainingSeconds).padStart(2, "0")}`;
}

function formatDate(value: string | null): string {
  if (value === null) {
    return "Not recorded";
  }
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
  }).format(new Date(value));
}

function formatNumber(value: number | null): string {
  if (value === null) {
    return "Not recorded";
  }
  return value.toLocaleString();
}
