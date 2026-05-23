import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { fetchVideo } from "../api";
import { ProgressTimeline } from "../components/ProgressTimeline";
import { StatusPill } from "../components/StatusPill";

const POLL_MS = 3000;

export function JobDetailPage() {
  const { id } = useParams<{ id: string }>();

  const videoQuery = useQuery({
    queryKey: ["video", id],
    queryFn: () => fetchVideo(id!),
    enabled: !!id,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "SUCCESS" || status === "ERROR") return false;
      return POLL_MS;
    },
  });

  const job = videoQuery.data;

  return (
    <div className="page">
      <header className="page-header">
        <Link to="/jobs" className="back-link">
          ← Jobs
        </Link>
        <h1>{job?.original_filename ?? "Job"}</h1>
        {job && (
          <p className="muted">
            {job.source} → {job.target} · {job.model_display_name}
          </p>
        )}
      </header>

      {videoQuery.isLoading && <p className="muted">Loading…</p>}
      {videoQuery.isError && (
        <p className="error">{(videoQuery.error as Error).message}</p>
      )}

      {job && (
        <section className="card">
          <div className="job-detail__status">
            <StatusPill status={job.status} />
            <span className="job-detail__progress">{job.progress}%</span>
          </div>
          <ProgressTimeline progress={job.progress} status={job.status} />
          {job.status === "ERROR" && job.error_message && (
            <p className="error">{job.error_message}</p>
          )}
          {job.status === "SUCCESS" && job.download_url && (
            <a href={job.download_url} className="btn btn--primary">
              Download translated video
            </a>
          )}
        </section>
      )}
    </div>
  );
}
