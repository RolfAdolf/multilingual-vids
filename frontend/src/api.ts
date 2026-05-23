const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

export type LanguageItem = {
  code: string;
  name_en: string;
  name_ru: string;
};

export type ModelMetrics = {
  bleu: number | null;
  dataset_name: string | null;
  measured_at: string | null;
};

export type ModelItem = {
  id: string;
  slug: string;
  display_name: string;
  description: string;
  provider: string;
  pipeline_summary: string;
  tags: string[];
  is_recommended: boolean;
  metrics: ModelMetrics | null;
};

export type ModelCatalogItem = ModelItem & {
  worker_queue: string;
  language_pairs: {
    source: string;
    target: string;
    source_name_en: string;
    target_name_en: string;
    bleu: number | null;
  }[];
};

export type CoverageCell = {
  supported: boolean;
  bleu: number | null;
  quality: "high" | "medium" | "low" | "none";
};

export type VideoJob = {
  id: string;
  original_filename: string;
  status: string;
  progress: number;
  source: string;
  target: string;
  model_id: string;
  model_slug: string;
  model_display_name: string;
  file_size_bytes: number | null;
  download_url: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  finished_at: string | null;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? res.statusText);
  }
  return res.json() as Promise<T>;
}

export function fetchLanguages() {
  return request<{ items: LanguageItem[] }>("/languages");
}

export function fetchModels(source: string, target: string) {
  return request<{
    source: string;
    target: string;
    recommended_model_id: string | null;
    items: ModelItem[];
  }>(`/models?source=${encodeURIComponent(source)}&target=${encodeURIComponent(target)}`);
}

export function fetchModelsCatalog() {
  return request<{ items: ModelCatalogItem[] }>("/models/catalog");
}

export function fetchModelsCoverage() {
  return request<{
    languages: { code: string; name_en: string; name_ru: string }[];
    items: {
      id: string;
      slug: string;
      display_name: string;
      coverage: Record<string, CoverageCell>;
    }[];
  }>("/models/coverage");
}

export function fetchVideos(status?: string) {
  const q = status ? `?status=${encodeURIComponent(status)}` : "";
  return request<{ items: VideoJob[] }>(`/videos${q}`);
}

export function createUploadUrl(filename: string, contentType: string, sizeBytes: number) {
  return request<{
    upload_url: string;
    object_key: string;
    expires_in: number;
    method: string;
    headers: Record<string, string>;
  }>("/videos/upload-url", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      filename,
      content_type: contentType,
      size_bytes: sizeBytes,
    }),
  });
}

export function createVideo(
  objectKey: string,
  source: string,
  target: string,
  modelId: string,
  originalFilename?: string
) {
  return request<VideoJob>("/videos", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      object_key: objectKey,
      source,
      target,
      model_id: modelId,
      ...(originalFilename ? { original_filename: originalFilename } : {}),
    }),
  });
}

export function fetchVideo(id: string) {
  return request<VideoJob>(`/videos/${id}`);
}
