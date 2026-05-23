import { Link } from "react-router-dom";
import type { VideoJob } from "../api";
import { ProgressTimeline } from "./ProgressTimeline";
import { StatusPill } from "./StatusPill";

function formatSize(bytes: number | null): string {
  if (bytes == null) return "—";
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

export function JobsTable({ jobs }: { jobs: VideoJob[] }) {
  if (!jobs.length) {
    return <p className="empty-state">No jobs yet. Create one from New Job.</p>;
  }

  return (
    <div className="table-wrap">
      <table className="jobs-table">
        <thead>
          <tr>
            <th>File</th>
            <th>Pair</th>
            <th>Model</th>
            <th>Status</th>
            <th>Progress</th>
            <th>Created</th>
            <th>Output</th>
          </tr>
        </thead>
        <tbody>
          {jobs.map((job) => (
            <tr key={job.id}>
              <td>
                <strong>{job.original_filename || job.id.slice(0, 8)}</strong>
                <span className="muted">{formatSize(job.file_size_bytes)}</span>
              </td>
              <td>
                {job.source} → {job.target}
              </td>
              <td>{job.model_display_name || job.model_slug}</td>
              <td>
                <StatusPill status={job.status} />
              </td>
              <td className="jobs-table__progress">
                <span>{job.progress}%</span>
                <ProgressTimeline progress={job.progress} status={job.status} compact />
              </td>
              <td className="muted">{formatDate(job.created_at)}</td>
              <td>
                {job.status === "SUCCESS" && job.download_url ? (
                  <a href={job.download_url} className="btn btn--small">
                    Download
                  </a>
                ) : job.status === "ERROR" ? (
                  <span className="error-inline" title={job.error_message ?? undefined}>
                    Failed
                  </span>
                ) : (
                  <Link to={`/jobs/${job.id}`} className="btn btn--ghost btn--small">
                    View
                  </Link>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
