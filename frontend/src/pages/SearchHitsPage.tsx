import { Alert, Button, Stack, TextField } from "@mui/material";
import type { FormEvent } from "react";
import { useCallback, useEffect, useState } from "react";

import { getSearchHits } from "../api/client";
import type { SearchHitListResponse } from "../api/types";
import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { PageHeader } from "../components/PageHeader";
import { SearchHitsTable } from "../components/SearchHitsTable";

const PAGE_LIMIT = 50;

type SearchHitsState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; searchHits: SearchHitListResponse };

export function SearchHitsPage() {
  const [searchHitsState, setSearchHitsState] = useState<SearchHitsState>({
    status: "loading",
  });
  const [queryTextInput, setQueryTextInput] = useState("");
  const [appliedQueryText, setAppliedQueryText] = useState("");

  const loadSearchHits = useCallback(() => {
    setSearchHitsState({ status: "loading" });
    getSearchHits({
      limit: PAGE_LIMIT,
      offset: 0,
      queryText: appliedQueryText,
    })
      .then((searchHits) => {
        setSearchHitsState({ status: "ready", searchHits });
      })
      .catch((error: unknown) => {
        const message =
          error instanceof Error ? error.message : "Unable to load search-hit provenance";
        setSearchHitsState({ status: "error", message });
      });
  }, [appliedQueryText]);

  useEffect(() => {
    loadSearchHits();
  }, [loadSearchHits]);

  function handleSearchSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAppliedQueryText(queryTextInput.trim());
  }

  return (
    <Stack spacing={3}>
      <PageHeader
        description="Browse the query and collection-run context that discovered stored videos."
        title="Search-Hit Provenance"
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
          label="Filter by query text"
          onChange={(event) => setQueryTextInput(event.target.value)}
          size="small"
          value={queryTextInput}
        />
        <Button type="submit" variant="contained">
          Search
        </Button>
      </Stack>
      <Alert severity="info">
        Showing up to {PAGE_LIMIT} search-hit provenance records from the current API query.
      </Alert>
      {searchHitsState.status === "loading" ? <LoadingState /> : null}
      {searchHitsState.status === "error" ? (
        <ErrorState message={searchHitsState.message} onRetry={loadSearchHits} />
      ) : null}
      {searchHitsState.status === "ready" ? (
        <SearchHitsTable searchHits={searchHitsState.searchHits.items} />
      ) : null}
    </Stack>
  );
}
