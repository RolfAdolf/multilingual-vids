import logging
import subprocess
from pathlib import Path


logger = logging.getLogger(__name__)


class FFmpegVideoService:
    def extract_audio(self, *, video_path: str, audio_path: str) -> None:
        Path(audio_path).parent.mkdir(parents=True, exist_ok=True)
        self._run(
            [
                "ffmpeg",
                "-y",
                "-i",
                video_path,
                "-vn",
                "-ac",
                "1",
                "-ar",
                "16000",
                audio_path,
            ]
        )

    def replace_audio(self, *, video_path: str, audio_path: str, output_path: str) -> None:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        self._run(
            [
                "ffmpeg",
                "-y",
                "-i",
                video_path,
                "-i",
                audio_path,
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-c:v",
                "copy",
                "-shortest",
                output_path,
            ]
        )

    @staticmethod
    def _run(command: list[str]) -> None:
        logger.info("Running ffmpeg command command=%s", " ".join(command))
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            logger.error("FFmpeg command failed returncode=%s stderr=%s", result.returncode, result.stderr.strip())
            raise RuntimeError(result.stderr.strip() or f"Command failed: {' '.join(command)}")
        logger.info("FFmpeg command completed successfully")
