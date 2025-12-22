export interface Competitor {
  id: number;
  name: string;
  url: string;
  priority: number;
  enabled: boolean;
  created_at?: string;
}

export interface SEOResponse {
  title?: string;
  meta_description?: string;
  meta_keywords?: string;
  h1_tags?: string[];
  h2_tags?: string[];
  robots_txt?: string;
  sitemap_url?: string;
  structured_data?: Record<string, unknown>;
  internal_links_count?: number;
  external_links_count?: number;
  page_load_time?: number;
  collected_at?: string;
}

export interface ScanStatus {
  status: "queued" | "running" | "completed" | "failed";
  progress: number;
  result?: Record<string, unknown>;
  error?: string;
}
