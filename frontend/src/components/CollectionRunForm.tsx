import { Alert, Button, Paper, Stack, TextField, Typography } from "@mui/material";
import type { FormEvent } from "react";
import { useEffect, useState } from "react";

import { createCollectionRun } from "../api/client";
import type { CollectionRunCreateResponse } from "../api/types";

const DEFAULT_MAX_RESULTS = 10;
const MIN_MAX_RESULTS = 1;
const MAX_BROWSER_RESULTS = 25;

type CollectionRunFormProps = {
  initialQuery: string;
  onCollected: (result: CollectionRunCreateResponse) => void;
};

export function CollectionRunForm({ initialQuery, onCollected }: CollectionRunFormProps) {
  const [query, setQuery] = useState(initialQuery);
  const [maxResults, setMaxResults] = useState(DEFAULT_MAX_RESULTS);
  const [collecting, setCollecting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (initialQuery.trim()) {
      setQuery(initialQuery);
    }
  }, [initialQuery]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedQuery = query.trim();
    if (!trimmedQuery) {
      setErrorMessage("Enter a YouTube metadata search query.");
      return;
    }

    setCollecting(true);
    setErrorMessage(null);
    createCollectionRun({
      query: trimmedQuery,
      max_results: maxResults,
    })
      .then((result) => {
        onCollected(result);
      })
      .catch((error: unknown) => {
        const message =
          error instanceof Error ? error.message : "Unable to collect YouTube metadata";
        setErrorMessage(message);
      })
      .finally(() => {
        setCollecting(false);
      });
  }

  return (
    <Paper component="section" sx={{ p: 2 }}>
      <Stack component="form" onSubmit={handleSubmit} spacing={2}>
        <Typography component="h2" variant="h2">
          Collect Metadata
        </Typography>
        {errorMessage ? <Alert severity="error">{errorMessage}</Alert> : null}
        <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
          <TextField
            fullWidth
            label="YouTube search query"
            onChange={(event) => setQuery(event.target.value)}
            size="small"
            value={query}
          />
          <TextField
            inputProps={{ max: MAX_BROWSER_RESULTS, min: MIN_MAX_RESULTS }}
            label="Max results"
            onChange={(event) => setMaxResults(Number(event.target.value))}
            size="small"
            sx={{ width: { xs: "100%", md: 160 } }}
            type="number"
            value={maxResults}
          />
          <Button
            disabled={collecting || !query.trim()}
            sx={{ minWidth: 180 }}
            type="submit"
            variant="contained"
          >
            {collecting ? "Collecting" : "Collect metadata"}
          </Button>
        </Stack>
      </Stack>
    </Paper>
  );
}
