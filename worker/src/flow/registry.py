from flow.seamless.pipeline import SeamlessPipeline
from flow.zeroshot.pipeline import ZeroshotPipeline
from flow.zeroswot.pipeline import ZeroSwotPipeline


_PIPELINES = {
    "seamless_m4t": SeamlessPipeline,
    "zeroswot": ZeroSwotPipeline,
    "zeroshot": ZeroshotPipeline,
}


def get_pipeline(model_slug: str):
    try:
        cls = _PIPELINES[model_slug]
    except KeyError as exc:
        raise ValueError(f"Unknown model slug: {model_slug}") from exc
    return cls()
