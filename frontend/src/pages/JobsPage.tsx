import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { fetchVideos } from "../api";
import { JobsTable } from "../components/JobsTable";

const STATUSES = ["", "WAITING", "PROCESSING", "SUCCESS", "ERROR"] as const;

export function JobsPage() {
  const [status, setStatus] = useState("");

  const videosQuery = useQuery({
    queryKey: ["videos", status],
    queryFn: () => fetchVideos(status || undefined),
    refetchInterval: 3000,
  });

  return (
    <div className="page">
      <header className="page-header page-header--row">
        <div>
          <h1>Jobs Dashboard</h1>
          <p className="muted">Track translation pipelines and download results.</p>
        </div>
        <div className="page-header__actions">
          <label className="filter-label">
            Status
            <select value={status} onChange={(e) => setStatus(e.target.value)}>
              {STATUSES.map((s) => (
                <option key={s || "all"} value={s}>
                  {s || "All"}
                </option>
              ))}
            </select>
          </label>
          <Link to="/" className="btn btn--primary">
            New Job
          </Link>
        </div>
      </header>

      <section className="card">
        {videosQuery.isLoading && <p className="muted">Loading jobs…</p>}
        {videosQuery.isError && (
          <p className="error">{(videosQuery.error as Error).message}</p>
        )}
        {videosQuery.data && <JobsTable jobs={videosQuery.data.items} />}
      </section>
    </div>
  );
}
