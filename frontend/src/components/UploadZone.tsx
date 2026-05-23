import { DragEvent, useRef, useState } from "react";

const ACCEPT = "video/mp4,video/webm,video/quicktime,video/x-matroska";
const MAX_MB = 500;

type Props = {
  file: File | null;
  onFile: (file: File | null) => void;
};

export function UploadZone({ file, onFile }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);

  const pick = (f: File | undefined) => {
    if (!f) return;
    if (f.size > MAX_MB * 1024 * 1024) {
      alert(`File exceeds ${MAX_MB} MB limit`);
      return;
    }
    onFile(f);
  };

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    pick(e.dataTransfer.files[0]);
  };

  return (
    <div
      className={`upload-zone${dragOver ? " upload-zone--over" : ""}${file ? " upload-zone--filled" : ""}`}
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={onDrop}
      onClick={() => inputRef.current?.click()}
      onKeyDown={(e) => {
        if (e.key === "Enter") inputRef.current?.click();
      }}
      role="button"
      tabIndex={0}
    >
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPT}
        hidden
        onChange={(e) => pick(e.target.files?.[0])}
      />
      {file ? (
        <div className="upload-zone__summary">
          <strong>{file.name}</strong>
          <span>{(file.size / (1024 * 1024)).toFixed(1)} MB</span>
          <span>{file.type || "video/*"}</span>
          <button
            type="button"
            className="btn btn--ghost"
            onClick={(e) => {
              e.stopPropagation();
              onFile(null);
            }}
          >
            Remove
          </button>
        </div>
      ) : (
        <>
          <p className="upload-zone__title">Drag & drop a video file here</p>
          <p className="upload-zone__hint">or click to browse · MP4, WebM, MOV, MKV · max {MAX_MB} MB</p>
        </>
      )}
    </div>
  );
}
