from __future__ import annotations

import subprocess
from pathlib import Path


def extract_audio_mono_16k(video_path: Path, wav_path: Path) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            str(wav_path),
        ],
        check=True,
        capture_output=True,
    )


def mux_video_with_audio(video_path: Path, audio_path: Path, output_path: Path) -> None:
    subprocess.run(
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
        check=True,
        capture_output=True,
    )
