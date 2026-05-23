const STAGES = [
  { label: "Queued", min: 0 },
  { label: "Download", min: 10 },
  { label: "Extract", min: 20 },
  { label: "Translate", min: 35 },
  { label: "Mix", min: 75 },
  { label: "Upload", min: 90 },
  { label: "Done", min: 100 },
] as const;

function stageIndex(progress: number, status: string): number {
  if (status === "SUCCESS") return STAGES.length - 1;
  for (let i = STAGES.length - 1; i >= 0; i -= 1) {
    if (progress >= STAGES[i].min) return i;
  }
  return 0;
}

export function ProgressTimeline({
  progress,
  status,
  compact = false,
}: {
  progress: number;
  status: string;
  compact?: boolean;
}) {
  const active = stageIndex(progress, status);
  const pct = Math.min(100, Math.max(0, progress));

  return (
    <div className={`progress-timeline${compact ? " progress-timeline--compact" : ""}`}>
      <div className="progress-bar-track" aria-hidden>
        <div className="progress-bar-fill" style={{ width: `${pct}%` }} />
      </div>
      <div className="progress-stages">
        {STAGES.map((stage, i) => (
          <div
            key={stage.label}
            className={`progress-stage${i <= active ? " progress-stage--active" : ""}${
              i === active ? " progress-stage--current" : ""
            }`}
          >
            <span className="progress-stage-dot" />
            {!compact && <span className="progress-stage-label">{stage.label}</span>}
          </div>
        ))}
      </div>
    </div>
  );
}
