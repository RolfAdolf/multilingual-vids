const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

export type ModelItem = {
  id: string;
  slug: string;
  display_name: string;
  is_recommended: boolean;
  metrics: {
    bleu: number | null;
    nist: number | null;
    dataset_name: string | null;
    measured_at: string | null;
  } | null;
};

export type VideoJob = {
  id: string;
  status: string;
  progress: number;
  source: string;
  target: string;
  model_id: string;
  model_slug: string;
  download_url: string | null;
  error_message: string | null;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? res.statusText);
  }
  return res.json() as Promise<T>;
}

export function fetchModels(source: string, target: string) {
  return request<{
    recommended_model_id: string;
    items: ModelItem[];
  }>(`/models?source=${source}&target=${target}`);
}

export function createUploadUrl(filename: string, contentType: string, sizeBytes: number) {
  return request<{
    upload_url: string;
    object_key: string;
    expires_in: number;
    method: string;
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

export function createVideo(objectKey: string, source: string, target: string, modelId: string) {
  return request<VideoJob>("/videos", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      object_key: objectKey,
      source,
      target,
      model_id: modelId,
    }),
  });
}

export function fetchVideo(id: string) {
  return request<VideoJob>(`/videos/${id}`);
}
