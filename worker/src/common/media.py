from __future__ import annotations

import subprocess
from pathlib import Path


class MediaProcessingError(ValueError):
    """Invalid or unsupported input media (not retryable)."""


def local_input_path(tmp_dir: Path, object_key: str) -> Path:
    """Preserve the object extension so ffmpeg can probe the container format."""
    name = Path(object_key).name
    if not name or name in {".", ".."}:
        name = "source.mp4"
    return tmp_dir / name


def ensure_non_empty_file(path: Path) -> int:
    if not path.is_file():
        raise MediaProcessingError(f"Downloaded file is missing: {path}")
    size = path.stat().st_size
    if size <= 0:
        raise MediaProcessingError(f"Downloaded file is empty: {path}")
    return size


def assert_has_audio_stream(video_path: Path) -> None:
    proc = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "stream=codec_type",
            "-of",
            "csv=p=0",
            str(video_path),
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip() or f"ffprobe exit {proc.returncode}"
        raise MediaProcessingError(f"Cannot read media file ({video_path.name}): {stderr}")

    has_audio = any(line.strip() == "audio" for line in (proc.stdout or "").splitlines())
    if not has_audio:
        raise MediaProcessingError(
            "The uploaded video has no audio track. "
            "Upload a video file that contains speech or sound."
        )


def _run_ffmpeg(args: list[str], *, action: str) -> None:
    proc = subprocess.run(
        args,
        capture_output=True,
        text=True,
    )
    if proc.returncode == 0:
        return
    stderr = (proc.stderr or "").strip()
    tail = stderr[-4000:] if stderr else "(no stderr)"
    raise MediaProcessingError(f"ffmpeg {action} failed (exit {proc.returncode}): {tail}")


def extract_audio_mono_16k(video_path: Path, wav_path: Path) -> None:
    ensure_non_empty_file(video_path)
    assert_has_audio_stream(video_path)
    _run_ffmpeg(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-vn",
            "-map",
            "0:a:0",
            "-acodec",
            "pcm_s16le",
            "-ac",
            "1",
            "-ar",
            "16000",
            str(wav_path),
        ],
        action="audio extraction",
    )
    ensure_non_empty_file(wav_path)


def mux_video_with_audio(video_path: Path, audio_path: Path, output_path: Path) -> None:
    ensure_non_empty_file(video_path)
    ensure_non_empty_file(audio_path)
    _run_ffmpeg(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-i",
            str(audio_path),
            "-c:v",
            "copy",
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-shortest",
            str(output_path),
        ],
        action="mux",
    )
    ensure_non_empty_file(output_path)
