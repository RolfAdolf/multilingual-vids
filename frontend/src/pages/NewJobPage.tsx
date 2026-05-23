import { useMutation, useQuery } from "@tanstack/react-query";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  createUploadUrl,
  createVideo,
  fetchLanguages,
  fetchModels,
} from "../api";
import { ModelCard } from "../components/ModelCard";
import { UploadZone } from "../components/UploadZone";

const POLL_HINT = "Status updates every 3 sec";

export function NewJobPage() {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [source, setSource] = useState("de");
  const [target, setTarget] = useState("uk");
  const [modelId, setModelId] = useState("");
  const [error, setError] = useState<string | null>(null);

  const languagesQuery = useQuery({
    queryKey: ["languages"],
    queryFn: fetchLanguages,
  });

  const modelsQuery = useQuery({
    queryKey: ["models", source, target],
    queryFn: () => fetchModels(source, target),
    enabled: Boolean(source && target && source !== target),
  });

  useEffect(() => {
    const rec = modelsQuery.data?.recommended_model_id;
    if (rec) setModelId(rec);
  }, [modelsQuery.data?.recommended_model_id, source, target]);

  const languages = languagesQuery.data?.items ?? [];

  const swapLanguages = () => {
    setSource(target);
    setTarget(source);
  };

  const uploadMutation = useMutation({
    mutationFn: async () => {
      if (!file || !modelId) throw new Error("Select a video file and a model");
      setError(null);
      const { upload_url, object_key, headers } = await createUploadUrl(
        file.name,
        file.type || "video/mp4",
        file.size
      );
      let put: Response;
      try {
        put = await fetch(upload_url, {
          method: "PUT",
          body: file,
          headers: {
            ...headers,
            "Content-Length": String(file.size),
          },
        });
      } catch {
        throw new Error(
          "Upload to storage failed (network/CORS). Run: docker compose exec core-api python manage.py configure_s3_cors"
        );
      }
      if (!put.ok) {
        const detail = await put.text().catch(() => "");
        throw new Error(
          `Upload to storage failed: HTTP ${put.status}${detail ? ` — ${detail.slice(0, 200)}` : ""}`
        );
      }
      return createVideo(object_key, source, target, modelId, file.name);
    },
    onSuccess: (job) => navigate(`/jobs/${job.id}`),
    onError: (err: unknown) =>
      setError(err instanceof Error ? err.message : "Upload failed"),
  });

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    uploadMutation.mutate();
  };

  const kpiChips = useMemo(
    () => ["Max 500 MB", "MP4 · WebM · MOV · MKV", POLL_HINT, "Result retention 30 days"],
    []
  );

  return (
    <div className="page-grid page-grid--studio">
      <div className="page-main">
        <header className="page-header">
          <h1>New Translation Job Studio</h1>
          <p>Upload a video and configure your translation job.</p>
          <ul className="kpi-chips">
            {kpiChips.map((chip) => (
              <li key={chip}>{chip}</li>
            ))}
          </ul>
        </header>

        <form onSubmit={onSubmit} className="studio-form">
          <section className="card">
            <h2>Video</h2>
            <UploadZone file={file} onFile={setFile} />
          </section>

          <section className="card card--row">
            <h2>Language pair</h2>
            <div className="lang-row">
              <label>
                Source
                <select value={source} onChange={(e) => setSource(e.target.value)}>
                  {languages.map((l) => (
                    <option key={`s-${l.code}`} value={l.code}>
                      {l.name_en} ({l.code})
                    </option>
                  ))}
                </select>
              </label>
              <button type="button" className="btn btn--ghost" onClick={swapLanguages} title="Swap">
                ⇄
              </button>
              <label>
                Target
                <select value={target} onChange={(e) => setTarget(e.target.value)}>
                  {languages.map((l) => (
                    <option key={`t-${l.code}`} value={l.code}>
                      {l.name_en} ({l.code})
                    </option>
                  ))}
                </select>
              </label>
            </div>
          </section>

          <section className="card">
            <h2>Select a model</h2>
            {source === target && (
              <p className="error">Source and target languages must differ.</p>
            )}
            {modelsQuery.isLoading && <p className="muted">Loading models…</p>}
            {modelsQuery.isError && (
              <p className="error">{(modelsQuery.error as Error).message}</p>
            )}
            <div className="model-grid">
              {modelsQuery.data?.items.map((m) => (
                <ModelCard
                  key={m.id}
                  model={m}
                  selected={modelId === m.id}
                  onSelect={() => setModelId(m.id)}
                />
              ))}
            </div>
          </section>

          <footer className="form-actions">
            <button
              type="button"
              className="btn btn--ghost"
              onClick={() => {
                setFile(null);
                setError(null);
              }}
            >
              Reset
            </button>
            <button
              type="submit"
              className="btn btn--primary"
              disabled={
                !file ||
                !modelId ||
                source === target ||
                uploadMutation.isPending
              }
            >
              {uploadMutation.isPending ? "Uploading…" : "Create Job"}
            </button>
          </footer>
          {error && <p className="error">{error}</p>}
        </form>
      </div>

      <aside className="info-panel card">
        <h2>Upload & processing</h2>
        <ul className="info-list">
          <li>Presigned PUT upload, link expires in ~15 min</li>
          <li>ffprobe validation on worker</li>
          <li>Async pipeline: STT → MT → TTS (model-dependent)</li>
          <li>{POLL_HINT} after job is created</li>
        </ul>
        <h3>Secure upload</h3>
        <p className="muted">Files go directly to object storage; API never stores raw video bytes.</p>
      </aside>
    </div>
  );
}
