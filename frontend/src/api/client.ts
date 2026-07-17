import type {
  CollectionRunCreateResponse,
  CreateCollectionRunRequest,
  HealthResponse,
  RunListResponse,
  SearchHitListResponse,
  SummaryResponse,
  UpdateVideoAnnotationRequest,
  VideoAnnotationResponse,
  VideoDetailResponse,
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

type FetchJsonOptions = {
  method?: "GET" | "PATCH" | "POST";
  body?: unknown;
};

async function fetchJson<TResponse>(
  path: string,
  options: FetchJsonOptions = {},
): Promise<TResponse> {
  const method = options.method ?? "GET";
  const headers: Record<string, string> = {
    Accept: "application/json",
  };
  if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    method,
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
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

export function getVideo(youtubeVideoId: string): Promise<VideoDetailResponse> {
  return fetchJson<VideoDetailResponse>(`/api/videos/${encodeURIComponent(youtubeVideoId)}`);
}

export function updateVideoAnnotation(
  youtubeVideoId: string,
  payload: UpdateVideoAnnotationRequest,
): Promise<VideoAnnotationResponse> {
  return fetchJson<VideoAnnotationResponse>(
    `/api/videos/${encodeURIComponent(youtubeVideoId)}/annotation`,
    {
      method: "PATCH",
      body: payload,
    },
  );
}

export function createCollectionRun(
  payload: CreateCollectionRunRequest,
): Promise<CollectionRunCreateResponse> {
  return fetchJson<CollectionRunCreateResponse>("/api/collection-runs", {
    method: "POST",
    body: payload,
  });
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
