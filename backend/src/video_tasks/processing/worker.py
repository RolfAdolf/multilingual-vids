import asyncio
import logging
import time
from pathlib import Path

from core.settings import app_settings
from database import async_session_maker
from video_tasks.models import VideoTaskStatus
from video_tasks.processing.factory import get_video_translator
from video_tasks.processing.video import FFmpegVideoService
from video_tasks.repo import VideoTaskRepo


logger = logging.getLogger(__name__)


async def process_video_task(task_id: str) -> None:
    started_at = time.monotonic()
    logger.info("Video task worker started task_id=%s", task_id)
    async with async_session_maker() as session:
        repo = VideoTaskRepo(session)
        task = await repo.get_task(task_id)
        if task is None:
            logger.warning("Video task %s was not found", task_id)
            return

        logger.info(
            "Video task loaded task_id=%s input_path=%s source_lang=%s target_lang=%s",
            task_id,
            task.input_path,
            task.source_lang,
            task.target_lang,
        )
        await repo.set_status(task_id, VideoTaskStatus.PROCESSING)
        logger.info("Video task status changed task_id=%s status=%s", task_id, VideoTaskStatus.PROCESSING)

        try:
            paths = _build_processing_paths(task_id)
            logger.info(
                "Video task processing paths prepared task_id=%s extracted_audio=%s translated_audio=%s output_video=%s",
                task_id,
                paths["extracted_audio"],
                paths["translated_audio"],
                paths["output_video"],
            )
            await asyncio.to_thread(
                _process_sync,
                task_id=task_id,
                input_path=task.input_path,
                source_lang=task.source_lang,
                target_lang=task.target_lang,
                extracted_audio_path=str(paths["extracted_audio"]),
                translated_audio_path=str(paths["translated_audio"]),
                output_path=str(paths["output_video"]),
            )
            logger.info("Persisting successful video task result task_id=%s", task_id)
            await repo.set_processing_paths(
                task_id,
                extracted_audio_path=str(paths["extracted_audio"]),
                translated_audio_path=str(paths["translated_audio"]),
                output_path=str(paths["output_video"]),
            )
            logger.info(
                "Video task finished task_id=%s status=%s duration_seconds=%.2f",
                task_id,
                VideoTaskStatus.SUCCESS,
                time.monotonic() - started_at,
            )
        except Exception as exc:
            logger.exception(
                "Video task failed task_id=%s duration_seconds=%.2f",
                task_id,
                time.monotonic() - started_at,
            )
            await repo.set_error(task_id, str(exc))
            logger.info("Video task status changed task_id=%s status=%s", task_id, VideoTaskStatus.ERROR)


def _build_processing_paths(task_id: str) -> dict[str, Path]:
    task_dir = app_settings.storage_dir / "tasks" / task_id
    return {
        "extracted_audio": task_dir / "source.wav",
        "translated_audio": task_dir / "translated.wav",
        "output_video": task_dir / "translated.mp4",
    }


def _process_sync(
    *,
    task_id: str,
    input_path: str,
    source_lang: str,
    target_lang: str,
    extracted_audio_path: str,
    translated_audio_path: str,
    output_path: str,
) -> None:
    video_service = FFmpegVideoService()
    translator = get_video_translator()

    logger.info("Extracting source audio task_id=%s input_path=%s", task_id, input_path)
    video_service.extract_audio(video_path=input_path, audio_path=extracted_audio_path)
    logger.info("Source audio extracted task_id=%s audio_path=%s", task_id, extracted_audio_path)

    logger.info(
        "Translating audio task_id=%s source_lang=%s target_lang=%s",
        task_id,
        source_lang,
        target_lang,
    )
    translator.translate_audio(
        input_audio_path=extracted_audio_path,
        output_audio_path=translated_audio_path,
        source_lang=source_lang,
        target_lang=target_lang,
    )
    logger.info("Translated audio saved task_id=%s audio_path=%s", task_id, translated_audio_path)

    logger.info("Replacing video audio track task_id=%s output_path=%s", task_id, output_path)
    video_service.replace_audio(video_path=input_path, audio_path=translated_audio_path, output_path=output_path)
    logger.info("Video with translated audio saved task_id=%s output_path=%s", task_id, output_path)
