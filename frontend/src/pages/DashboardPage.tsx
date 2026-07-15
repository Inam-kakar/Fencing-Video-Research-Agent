import { Alert, Card, CardContent, Chip, Stack, Typography } from "@mui/material";
import { useCallback, useEffect, useState } from "react";

import { getHealth, getSummary } from "../api/client";
import type { HealthResponse, SummaryResponse } from "../api/types";
import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { SummaryCard } from "../components/SummaryCard";

type DashboardState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; health: HealthResponse; summary: SummaryResponse };

const summaryCards: Array<{
  key: keyof SummaryResponse;
  label: string;
  detail: string;
}> = [
  {
    key: "video_count",
    label: "Stored videos",
    detail: "Unique YouTube videos in the local database",
  },
  {
    key: "collection_run_count",
    label: "Collection runs",
    detail: "Recorded search sessions",
  },
  {
    key: "search_hit_count",
    label: "Search hits",
    detail: "Run-to-video provenance records",
  },
  {
    key: "annotation_count",
    label: "Annotations",
    detail: "Videos with local review records",
  },
  {
    key: "reviewed_count",
    label: "Reviewed",
    detail: "Videos marked reviewed",
  },
  {
    key: "unreviewed_count",
    label: "Unreviewed",
    detail: "Videos not yet marked reviewed",
  },
];

export function DashboardPage() {
  const [dashboardState, setDashboardState] = useState<DashboardState>({ status: "loading" });

  const loadDashboard = useCallback(() => {
    setDashboardState({ status: "loading" });
    Promise.all([getHealth(), getSummary()])
      .then(([health, summary]) => {
        setDashboardState({ status: "ready", health, summary });
      })
      .catch((error: unknown) => {
        const message = error instanceof Error ? error.message : "Unable to load dashboard data";
        setDashboardState({ status: "error", message });
      });
  }, []);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  if (dashboardState.status === "loading") {
    return <LoadingState />;
  }

  if (dashboardState.status === "error") {
    return <ErrorState message={dashboardState.message} onRetry={loadDashboard} />;
  }

  return (
    <Stack spacing={4}>
      <Stack spacing={2}>
        <Chip
          color={dashboardState.health.status === "ok" ? "success" : "warning"}
          label={`API status: ${dashboardState.health.status}`}
          sx={{ alignSelf: "flex-start", fontWeight: 700 }}
        />
        <Stack spacing={1}>
          <Typography component="h1" variant="h1">
            Research Dashboard Overview
          </Typography>
          <Typography color="text.secondary" maxWidth="760px" variant="body1">
            Local summary counts from the read-only FastAPI backend.
          </Typography>
        </Stack>
      </Stack>

      <Stack direction="row" flexWrap="wrap" gap={2}>
        {summaryCards.map((card) => (
          <SummaryCard
            key={card.key}
            detail={card.detail}
            label={card.label}
            value={dashboardState.summary[card.key]}
          />
        ))}
      </Stack>

      <Card>
        <CardContent>
          <Stack spacing={2}>
            <Typography component="h2" variant="h2">
              Next Dashboard Milestones
            </Typography>
            <Alert severity="info">
              Videos, collection runs, and search-hit provenance tables are planned for later
              frontend milestones.
            </Alert>
          </Stack>
        </CardContent>
      </Card>
    </Stack>
  );
}
