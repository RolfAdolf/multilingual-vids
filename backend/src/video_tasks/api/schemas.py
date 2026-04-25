from datetime import datetime

from pydantic import BaseModel, Field

from video_tasks.models import VideoTaskStatus


class UploadVideoResponse(BaseModel):
    task_id: str = Field(..., description="Идентификатор задачи обработки видео")
    status: VideoTaskStatus = Field(..., description="Начальный статус задачи")


class VideoTaskStatusResponse(BaseModel):
    task_id: str
    status: VideoTaskStatus
    source_lang: str
    target_lang: str
    download_url: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
