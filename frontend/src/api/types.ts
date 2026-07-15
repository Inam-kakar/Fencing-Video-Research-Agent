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
