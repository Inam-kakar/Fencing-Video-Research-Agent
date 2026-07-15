import {
  Chip,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from "@mui/material";

import type { SearchHitListItemResponse } from "../api/types";
import { DataTableEmptyState } from "./DataTableEmptyState";

type SearchHitsTableProps = {
  searchHits: SearchHitListItemResponse[];
};

export function SearchHitsTable({ searchHits }: SearchHitsTableProps) {
  if (searchHits.length === 0) {
    return <DataTableEmptyState message="No search-hit provenance records found." />;
  }

  return (
    <TableContainer component={Paper}>
      <Table aria-label="Search-hit provenance table" size="small">
        <TableHead>
          <TableRow>
            <TableCell align="right">Run ID</TableCell>
            <TableCell>Query text</TableCell>
            <TableCell align="right">Rank</TableCell>
            <TableCell>Video title</TableCell>
            <TableCell>YouTube video ID</TableCell>
            <TableCell>Channel</TableCell>
            <TableCell>Discovered at</TableCell>
            <TableCell>Review status</TableCell>
            <TableCell>Relevance label</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {searchHits.map((hit) => (
            <TableRow key={`${hit.collection_run_id}-${hit.youtube_video_id}-${hit.rank ?? "none"}`}>
              <TableCell align="right">{hit.collection_run_id}</TableCell>
              <TableCell sx={{ minWidth: 220 }}>{hit.query_text}</TableCell>
              <TableCell align="right">{hit.rank ?? "Not recorded"}</TableCell>
              <TableCell sx={{ minWidth: 260 }}>{hit.title}</TableCell>
              <TableCell>{hit.youtube_video_id}</TableCell>
              <TableCell>{hit.channel_title}</TableCell>
              <TableCell>{formatDateTime(hit.discovered_at)}</TableCell>
              <TableCell>
                <Chip label={hit.review_status ?? "unreviewed"} size="small" />
              </TableCell>
              <TableCell>{hit.relevance_label ?? "Not labeled"}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}
