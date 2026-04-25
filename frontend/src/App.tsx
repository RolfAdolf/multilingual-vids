import { FormEvent, useEffect, useMemo, useState } from "react";

type TaskStatus = "WAITING" | "PROCESSING" | "SUCCESS" | "ERROR";

type UploadResponse = {
  task_id: string;
  status: TaskStatus;
};

type StatusResponse = {
  task_id: string;
  status: TaskStatus;
  source_lang: string;
  target_lang: string;
  download_url: string | null;
  error_message: string | null;
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8888";

export function App() {
  const [file, setFile] = useState<File | null>(null);
  const [sourceLang, setSourceLang] = useState("eng");
  const [targetLang, setTargetLang] = useState("rus");
  const [task, setTask] = useState<StatusResponse | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const downloadUrl = useMemo(() => {
    if (!task?.download_url) {
      return null;
    }
    return `${API_BASE_URL}${task.download_url}`;
  }, [task]);

  useEffect(() => {
    if (!task || task.status === "SUCCESS" || task.status === "ERROR") {
      return;
    }

    const interval = window.setInterval(async () => {
      const nextTask = await fetchTask(task.task_id);
      setTask(nextTask);
    }, 3000);

    return () => window.clearInterval(interval);
  }, [task]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) {
      setMessage("Выберите видеофайл");
      return;
    }

    setIsUploading(true);
    setMessage(null);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(
        `${API_BASE_URL}/videos/?source_lang=${sourceLang}&target_lang=${targetLang}`,
        {
          method: "POST",
          body: formData,
        },
      );
      if (!response.ok) {
        throw new Error(await response.text());
      }

      const uploaded = (await response.json()) as UploadResponse;
      setTask(await fetchTask(uploaded.task_id));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Не удалось загрузить видео");
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <main className="page">
      <section className="card">
        <p className="eyebrow">SeamlessM4T video translation</p>
        <h1>Перевод видео</h1>
        <p className="description">
          Загрузите видео, выберите языки SeamlessM4T и дождитесь готового файла с новой аудиодорожкой.
        </p>

        <form className="form" onSubmit={handleSubmit}>
          <label>
            Видео
            <input accept="video/*" type="file" onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
          </label>

          <div className="row">
            <label>
              Исходный язык
              <input value={sourceLang} onChange={(event) => setSourceLang(event.target.value)} />
            </label>
            <label>
              Язык перевода
              <input value={targetLang} onChange={(event) => setTargetLang(event.target.value)} />
            </label>
          </div>

          <button disabled={isUploading} type="submit">
            {isUploading ? "Загрузка..." : "Загрузить и перевести"}
          </button>
        </form>

        {message && <p className="error">{message}</p>}
        {task && (
          <section className="status">
            <h2>Задача {task.task_id}</h2>
            <p>
              Статус: <strong>{task.status}</strong>
            </p>
            <p>
              Направление: {task.source_lang} {"->"} {task.target_lang}
            </p>
            {task.error_message && <p className="error">{task.error_message}</p>}
            {downloadUrl && (
              <a className="download" href={downloadUrl}>
                Скачать результат
              </a>
            )}
          </section>
        )}
      </section>
    </main>
  );
}

async function fetchTask(taskId: string): Promise<StatusResponse> {
  const response = await fetch(`${API_BASE_URL}/videos/${taskId}`);
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}
