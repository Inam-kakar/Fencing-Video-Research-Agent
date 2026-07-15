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

import type { RunListItemResponse } from "../api/types";
import { DataTableEmptyState } from "./DataTableEmptyState";

type RunsTableProps = {
  runs: RunListItemResponse[];
};

export function RunsTable({ runs }: RunsTableProps) {
  if (runs.length === 0) {
    return <DataTableEmptyState message="No collection runs found." />;
  }

  return (
    <TableContainer component={Paper}>
      <Table aria-label="Collection runs table" size="small">
        <TableHead>
          <TableRow>
            <TableCell align="right">Run ID</TableCell>
            <TableCell>Query text</TableCell>
            <TableCell>Status</TableCell>
            <TableCell>Started</TableCell>
            <TableCell>Completed</TableCell>
            <TableCell align="right">Hit count</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {runs.map((run) => (
            <TableRow key={run.run_id}>
              <TableCell align="right">{run.run_id}</TableCell>
              <TableCell sx={{ minWidth: 260 }}>{run.query_text}</TableCell>
              <TableCell>
                <Chip color={run.status === "completed" ? "success" : "warning"} label={run.status} size="small" />
              </TableCell>
              <TableCell>{formatDateTime(run.started_at)}</TableCell>
              <TableCell>{formatDateTime(run.completed_at)}</TableCell>
              <TableCell align="right">{run.hit_count.toLocaleString()}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}

function formatDateTime(value: string | null): string {
  if (value === null) {
    return "Not recorded";
  }
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}
