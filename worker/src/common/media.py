from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


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


def probe_media_duration_sec(path: Path) -> float:
    proc = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip() or f"ffprobe exit {proc.returncode}"
        raise MediaProcessingError(f"Cannot read duration of {path.name}: {stderr}")
    try:
        return float((proc.stdout or "").strip())
    except ValueError as exc:
        raise MediaProcessingError(f"Invalid duration from ffprobe for {path.name}") from exc


def _atempo_filter_chain(tempo: float) -> str:
    """Build ffmpeg atempo chain; each factor must stay in [0.5, 2.0]."""
    filters: list[str] = []
    remaining = tempo
    while remaining > 2.0:
        filters.append("atempo=2.0")
        remaining /= 2.0
    while remaining < 0.5:
        filters.append("atempo=0.5")
        remaining /= 0.5
    filters.append(f"atempo={remaining:.6f}")
    return ",".join(filters)


def match_audio_duration(
    reference_wav: Path,
    audio_wav: Path,
    output_wav: Path,
    *,
    tolerance_sec: float = 0.15,
) -> dict[str, float]:
    """
    Time-stretch audio_wav so its duration matches reference_wav (pitch-preserving atempo).
    Returns before/after durations in seconds.
    """
    ensure_non_empty_file(reference_wav)
    ensure_non_empty_file(audio_wav)
    ref_sec = probe_media_duration_sec(reference_wav)
    src_sec = probe_media_duration_sec(audio_wav)
    if ref_sec <= 0 or src_sec <= 0:
        raise MediaProcessingError("Cannot match duration: reference or audio length is zero")

    if abs(ref_sec - src_sec) <= tolerance_sec:
        if audio_wav.resolve() != output_wav.resolve():
            shutil.copyfile(audio_wav, output_wav)
        return {"reference_sec": ref_sec, "source_sec": src_sec, "output_sec": src_sec, "stretched": 0.0}

    # output_duration = input_duration / tempo  =>  tempo = src_sec / ref_sec
    tempo = src_sec / ref_sec
    filter_chain = _atempo_filter_chain(tempo)
    _run_ffmpeg(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(audio_wav),
            "-af",
            filter_chain,
            str(output_wav),
        ],
        action="audio duration match",
    )
    ensure_non_empty_file(output_wav)
    out_sec = probe_media_duration_sec(output_wav)
    logger.info(
        "Matched audio duration %.2fs -> %.2fs (target %.2fs, tempo=%.4f)",
        src_sec,
        out_sec,
        ref_sec,
        tempo,
    )
    return {
        "reference_sec": ref_sec,
        "source_sec": src_sec,
        "output_sec": out_sec,
        "stretched": 1.0,
        "atempo": tempo,
    }


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
            str(output_path),
        ],
        action="mux",
    )
    ensure_non_empty_file(output_path)
