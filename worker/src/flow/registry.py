import logging

from config.json_log import log_event
from common.pipeline_base import TranslationPipeline

logger = logging.getLogger(__name__)


def get_pipeline(model_slug: str, *, task_id: str | None = None) -> TranslationPipeline:
    log_event(
        logger,
        logging.INFO,
        "worker.pipeline.resolve",
        layer="pipeline",
        task_id=task_id,
        model_slug=model_slug,
    )
    if model_slug == "seamless_m4t":
        from flow.seamless.pipeline import SeamlessPipeline

        return SeamlessPipeline()
    if model_slug == "zeroswot":
        from flow.zeroswot.pipeline import ZeroSwotPipeline

        return ZeroSwotPipeline()
    if model_slug == "zeroshot":
        from flow.zeroshot.pipeline import ZeroshotPipeline

        return ZeroshotPipeline()
    log_event(
        logger,
        logging.ERROR,
        "worker.pipeline.unknown_slug",
        layer="pipeline",
        task_id=task_id,
        model_slug=model_slug,
    )
    raise ValueError(f"Unknown model slug: {model_slug}")
