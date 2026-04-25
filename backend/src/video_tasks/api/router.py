import logging
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from core.settings import app_settings
from video_tasks.api.schemas import UploadVideoResponse, VideoTaskStatusResponse
from video_tasks.models import VideoTaskStatus
from video_tasks.processing.worker import process_video_task
from video_tasks.repo import VideoTaskRepo


router = APIRouter(prefix="/videos", tags=["Videos"])
logger = logging.getLogger(__name__)


@router.post("/", status_code=201)
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    source_lang: str = "eng",
    target_lang: str = "rus",
    repo: VideoTaskRepo = Depends(VideoTaskRepo),
) -> UploadVideoResponse:
    task_id = str(uuid.uuid4())
    logger.info(
        "Received video upload task_id=%s filename=%s source_lang=%s target_lang=%s",
        task_id,
        file.filename,
        source_lang,
        target_lang,
    )
    input_path = _save_upload(file, task_id)
    logger.info("Saved uploaded video task_id=%s input_path=%s", task_id, input_path)

    task = await repo.create_task(
        task_id=task_id,
        original_filename=file.filename or "video",
        input_path=str(input_path),
        source_lang=source_lang,
        target_lang=target_lang,
    )
    logger.info("Created video task task_id=%s status=%s", task.id, task.status)
    background_tasks.add_task(process_video_task, task.id)
    logger.info("Scheduled video processing task_id=%s", task.id)
    return UploadVideoResponse(task_id=task.id, status=task.status)


@router.get("/{task_id}")
async def get_video_task_status(
    task_id: str,
    repo: VideoTaskRepo = Depends(VideoTaskRepo),
) -> VideoTaskStatusResponse:
    task = await repo.get_task(task_id)
    if task is None:
        logger.info("Video task status requested but task was not found task_id=%s", task_id)
        raise HTTPException(status_code=404, detail="Video task not found")
    logger.info("Video task status requested task_id=%s status=%s", task.id, task.status)

    return VideoTaskStatusResponse(
        task_id=task.id,
        status=task.status,
        source_lang=task.source_lang,
        target_lang=task.target_lang,
        download_url=f"/videos/{task.id}/download" if task.status == VideoTaskStatus.SUCCESS else None,
        error_message=task.error_message,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


@router.get("/{task_id}/download")
async def download_video(task_id: str, repo: VideoTaskRepo = Depends(VideoTaskRepo)) -> FileResponse:
    task = await repo.get_task(task_id)
    if task is None:
        logger.info("Video download requested but task was not found task_id=%s", task_id)
        raise HTTPException(status_code=404, detail="Video task not found")
    if task.status != VideoTaskStatus.SUCCESS or task.output_path is None:
        logger.info("Video download requested before ready task_id=%s status=%s", task.id, task.status)
        raise HTTPException(status_code=409, detail="Video is not ready")
    if not Path(task.output_path).exists():
        logger.error("Processed video file is missing task_id=%s output_path=%s", task.id, task.output_path)
        raise HTTPException(status_code=404, detail="Processed video file not found")

    logger.info("Serving processed video task_id=%s output_path=%s", task.id, task.output_path)
    return FileResponse(task.output_path, media_type="video/mp4", filename=f"translated-{task.original_filename}")


def _save_upload(file: UploadFile, task_id: str) -> Path:
    extension = Path(file.filename or "video.mp4").suffix or ".mp4"
    task_dir = app_settings.storage_dir / "tasks" / task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    input_path = task_dir / f"source{extension}"

    with input_path.open("wb") as destination:
        shutil.copyfileobj(file.file, destination)

    return input_path
