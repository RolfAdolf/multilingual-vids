from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_async_session
from video_tasks.models import VideoTask, VideoTaskStatus


class VideoTaskRepo:
    def __init__(self, session: AsyncSession = Depends(get_async_session)):
        self._session = session

    async def create_task(
        self,
        *,
        task_id: str,
        original_filename: str,
        input_path: str,
        source_lang: str,
        target_lang: str,
    ) -> VideoTask:
        task = VideoTask(
            id=task_id,
            original_filename=original_filename,
            input_path=input_path,
            source_lang=source_lang,
            target_lang=target_lang,
        )
        self._session.add(task)
        await self._session.commit()
        await self._session.refresh(task)
        return task

    async def get_task(self, task_id: str) -> VideoTask | None:
        result = await self._session.execute(select(VideoTask).where(VideoTask.id == task_id))
        return result.scalar_one_or_none()

    async def set_status(self, task_id: str, status: VideoTaskStatus) -> None:
        task = await self.get_task(task_id)
        if task is None:
            return
        task.status = status
        await self._session.commit()

    async def set_processing_paths(
        self,
        task_id: str,
        *,
        extracted_audio_path: str,
        translated_audio_path: str,
        output_path: str,
    ) -> None:
        task = await self.get_task(task_id)
        if task is None:
            return
        task.extracted_audio_path = extracted_audio_path
        task.translated_audio_path = translated_audio_path
        task.output_path = output_path
        task.status = VideoTaskStatus.SUCCESS
        task.error_message = None
        await self._session.commit()

    async def set_error(self, task_id: str, message: str) -> None:
        task = await self.get_task(task_id)
        if task is None:
            return
        task.status = VideoTaskStatus.ERROR
        task.error_message = message[:4000]
        await self._session.commit()
