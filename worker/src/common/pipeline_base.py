from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Protocol

from video.models import Video


ProgressCallback = Callable[[int], None]


@dataclass
class PipelineResult:
    output_object_key: str
    artifact_key: dict = field(default_factory=dict)


class TranslationPipeline(Protocol):
    def run(self, video: Video, progress_callback: ProgressCallback) -> PipelineResult: ...
