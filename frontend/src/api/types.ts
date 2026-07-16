export type HealthResponse = {
  status: string;
};

export type SummaryResponse = {
  video_count: number;
  collection_run_count: number;
  search_hit_count: number;
  annotation_count: number;
  reviewed_count: number;
  unreviewed_count: number;
};

export type VideoListItemResponse = {
  youtube_video_id: string;
  title: string;
  channel_title: string;
  duration_seconds: number | null;
  published_at: string | null;
  view_count: number | null;
  review_status: ReviewStatus | null;
  relevance_label: string | null;
  video_url: string | null;
  first_seen_at: string;
  last_refreshed_at: string;
};

export type VideoListResponse = {
  items: VideoListItemResponse[];
  count: number;
  limit: number;
  offset: number;
};

export type ReviewStatus = "unreviewed" | "reviewed";

export type VideoDetailResponse = {
  youtube_video_id: string;
  title: string;
  description: string | null;
  channel_id: string;
  channel_title: string;
  published_at: string | null;
  duration_seconds: number | null;
  view_count: number | null;
  like_count: number | null;
  comment_count: number | null;
  tags: string[];
  thumbnail_url: string | null;
  video_url: string | null;
  first_seen_at: string;
  last_refreshed_at: string;
  review_status: ReviewStatus | null;
  notes: string | null;
  relevance_label: string | null;
  competition_name: string | null;
  fencer_names: string[];
  weapon_category: string | null;
  event_notes: string | null;
  annotation_updated_at: string | null;
  discovery_run_count: number;
  first_collection_run_started_at: string | null;
  latest_collection_run_started_at: string | null;
  first_query_text: string | null;
  latest_query_text: string | null;
};

export type UpdateVideoAnnotationRequest = {
  review_status?: ReviewStatus;
  relevance_label?: string | null;
  notes?: string | null;
};

export type VideoAnnotationResponse = {
  youtube_video_id: string;
  review_status: ReviewStatus;
  relevance_label: string | null;
  notes: string | null;
  updated_at: string;
};

export type RunListItemResponse = {
  run_id: number;
  query_text: string;
  status: string;
  started_at: string;
  completed_at: string | null;
  hit_count: number;
};

export type RunListResponse = {
  items: RunListItemResponse[];
  count: number;
  limit: number;
  offset: number;
};

export type SearchHitListItemResponse = {
  collection_run_id: number;
  query_text: string;
  run_started_at: string;
  rank: number | null;
  discovered_at: string;
  youtube_video_id: string;
  title: string;
  channel_title: string;
  review_status: string | null;
  relevance_label: string | null;
};

export type SearchHitListResponse = {
  items: SearchHitListItemResponse[];
  count: number;
  limit: number;
  offset: number;
};
