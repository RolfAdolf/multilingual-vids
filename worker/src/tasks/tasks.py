"""Entry point for Celery autodiscover (imports all task modules)."""

from tasks.video import translate_video_task

__all__ = ["translate_video_task"]
