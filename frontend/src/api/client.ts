import type {
  HealthResponse,
  RunListResponse,
  SearchHitListResponse,
  SummaryResponse,
  VideoListResponse,
} from "./types";

const DEFAULT_API_BASE_URL = "http://localhost:8000";

type ListVideosParams = {
  limit: number;
  offset: number;
  search?: string;
};

type ListRunsParams = {
  limit: number;
  offset: number;
};

type ListSearchHitsParams = {
  limit: number;
  offset: number;
  queryText?: string;
};

function getApiBaseUrl(): string {
  const configuredUrl = import.meta.env.VITE_API_BASE_URL;
  const baseUrl = configuredUrl?.trim() || DEFAULT_API_BASE_URL;
  return baseUrl.replace(/\/+$/, "");
}

async function fetchJson<TResponse>(path: string): Promise<TResponse> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    method: "GET",
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`API request failed with status ${response.status}`);
  }

  return (await response.json()) as TResponse;
}

function toQueryString(params: Record<string, string | number | undefined>): string {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && String(value).trim() !== "") {
      query.set(key, String(value));
    }
  });
  return query.toString();
}

export function getHealth(): Promise<HealthResponse> {
  return fetchJson<HealthResponse>("/health");
}

export function getSummary(): Promise<SummaryResponse> {
  return fetchJson<SummaryResponse>("/api/summary");
}

export function getVideos({ limit, offset, search }: ListVideosParams): Promise<VideoListResponse> {
  const query = toQueryString({ limit, offset, search });
  return fetchJson<VideoListResponse>(`/api/videos?${query}`);
}

export function getRuns({ limit, offset }: ListRunsParams): Promise<RunListResponse> {
  const query = toQueryString({ limit, offset });
  return fetchJson<RunListResponse>(`/api/runs?${query}`);
}

export function getSearchHits({
  limit,
  offset,
  queryText,
}: ListSearchHitsParams): Promise<SearchHitListResponse> {
  const query = toQueryString({ limit, offset, query_text: queryText });
  return fetchJson<SearchHitListResponse>(`/api/search-hits?${query}`);
}
