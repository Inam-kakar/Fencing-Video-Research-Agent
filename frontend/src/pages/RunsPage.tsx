import { Alert, Stack } from "@mui/material";
import { useCallback, useEffect, useState } from "react";

import { getRuns } from "../api/client";
import type { RunListResponse } from "../api/types";
import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { PageHeader } from "../components/PageHeader";
import { RunsTable } from "../components/RunsTable";

const PAGE_LIMIT = 50;

type RunsState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; runs: RunListResponse };

export function RunsPage() {
  const [runsState, setRunsState] = useState<RunsState>({ status: "loading" });

  const loadRuns = useCallback(() => {
    setRunsState({ status: "loading" });
    getRuns({ limit: PAGE_LIMIT, offset: 0 })
      .then((runs) => {
        setRunsState({ status: "ready", runs });
      })
      .catch((error: unknown) => {
        const message = error instanceof Error ? error.message : "Unable to load collection runs";
        setRunsState({ status: "error", message });
      });
  }, []);

  useEffect(() => {
    loadRuns();
  }, [loadRuns]);

  return (
    <Stack spacing={3}>
      <PageHeader
        description="Review search sessions recorded during metadata collection."
        title="Collection Runs"
      />
      <Alert severity="info">Showing up to {PAGE_LIMIT} collection runs.</Alert>
      {runsState.status === "loading" ? <LoadingState /> : null}
      {runsState.status === "error" ? (
        <ErrorState message={runsState.message} onRetry={loadRuns} />
      ) : null}
      {runsState.status === "ready" ? <RunsTable runs={runsState.runs.items} /> : null}
    </Stack>
  );
}
