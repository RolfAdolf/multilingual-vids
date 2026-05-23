const STATUS_CLASS: Record<string, string> = {
  WAITING: "status-waiting",
  PROCESSING: "status-processing",
  SUCCESS: "status-success",
  ERROR: "status-error",
  UPLOAD: "status-upload",
};

const STATUS_LABEL: Record<string, string> = {
  WAITING: "Waiting",
  PROCESSING: "Processing",
  SUCCESS: "Success",
  ERROR: "Failed",
  UPLOAD: "Upload",
};

export function StatusPill({ status }: { status: string }) {
  const key = status.toUpperCase();
  return (
    <span className={`status-pill ${STATUS_CLASS[key] ?? "status-waiting"}`}>
      {STATUS_LABEL[key] ?? key}
    </span>
  );
}
