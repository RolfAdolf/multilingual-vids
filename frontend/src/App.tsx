import { useMutation, useQuery } from "@tanstack/react-query";
import { FormEvent, useEffect, useState } from "react";
import { createUploadUrl, createVideo, fetchModels, fetchVideo } from "./api";

const SOURCE = "de";
const TARGET = "uk";
const POLL_MS = 3000;

export default function App() {
  const [file, setFile] = useState<File | null>(null);
  const [modelId, setModelId] = useState<string>("");
  const [videoId, setVideoId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const modelsQuery = useQuery({
    queryKey: ["models", SOURCE, TARGET],
    queryFn: () => fetchModels(SOURCE, TARGET),
  });

  useEffect(() => {
    if (modelsQuery.data?.recommended_model_id && !modelId) {
      setModelId(modelsQuery.data.recommended_model_id);
    }
  }, [modelsQuery.data, modelId]);

  const videoQuery = useQuery({
    queryKey: ["video", videoId],
    queryFn: () => fetchVideo(videoId!),
    enabled: !!videoId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "SUCCESS" || status === "ERROR") return false;
      return POLL_MS;
    },
  });

  const uploadMutation = useMutation({
    mutationFn: async () => {
      if (!file || !modelId) throw new Error("Выберите файл и модель");
      setError(null);
      const { upload_url, object_key } = await createUploadUrl(
        file.name,
        file.type || "video/mp4",
        file.size
      );
      const put = await fetch(upload_url, {
        method: "PUT",
        body: file,
        headers: { "Content-Type": file.type || "video/mp4" },
      });
      if (!put.ok) throw new Error(`S3 upload failed: ${put.status}`);
      return createVideo(object_key, SOURCE, TARGET, modelId);
    },
    onSuccess: (job) => setVideoId(job.id),
    onError: (err: Error) => setError(err.message),
  });

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    uploadMutation.mutate();
  };

  const job = videoQuery.data;

  return (
    <div className="page">
      <header>
        <h1>Multilingual Videos</h1>
        <p>Перевод видео {SOURCE} → {TARGET}</p>
      </header>

      <section className="card">
        <h2>Модель</h2>
        {modelsQuery.isLoading && <p>Загрузка моделей…</p>}
        {modelsQuery.data && (
          <ul className="models">
            {modelsQuery.data.items.map((m) => (
              <li key={m.id}>
                <label>
                  <input
                    type="radio"
                    name="model"
                    value={m.id}
                    checked={modelId === m.id}
                    onChange={() => setModelId(m.id)}
                  />
                  <span className="title">{m.display_name}</span>
                  {m.is_recommended && <span className="badge">рекомендуется</span>}
                  {m.metrics && (
                    <span className="metrics">
                      BLEU {m.metrics.bleu?.toFixed(1) ?? "—"} · NIST{" "}
                      {m.metrics.nist?.toFixed(2) ?? "—"}
                    </span>
                  )}
                </label>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="card">
        <h2>Загрузка</h2>
        <form onSubmit={onSubmit}>
          <input
            type="file"
            accept="video/mp4,video/webm,video/quicktime,video/x-matroska"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
          <button type="submit" disabled={!file || uploadMutation.isPending}>
            {uploadMutation.isPending ? "Загрузка…" : "Перевести"}
          </button>
        </form>
        {error && <p className="error">{error}</p>}
      </section>

      {job && (
        <section className="card">
          <h2>Статус</h2>
          <p>
            <strong>{job.status}</strong> — {job.progress}%
          </p>
          {job.status === "ERROR" && job.error_message && (
            <p className="error">{job.error_message}</p>
          )}
          {job.status === "SUCCESS" && job.download_url && (
            <a href={job.download_url} className="download">
              Скачать результат
            </a>
          )}
        </section>
      )}
    </div>
  );
}
