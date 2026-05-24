import os
import sys
from pathlib import Path

import environ

from config.env_loader import read_env_files

BASE_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BASE_DIR.parent.parent


def _core_src() -> Path:
    explicit = os.environ.get("CORE_SRC_PATH", "")
    if explicit:
        return Path(explicit).resolve()
    for base in (ROOT_DIR, BASE_DIR.parent):
        candidate = (base / "core-api" / "src").resolve()
        if (candidate / "translation_models").is_dir():
            return candidate
    raise RuntimeError("core-api/src not found; set CORE_SRC_PATH or monorepo layout")


CORE_SRC = _core_src()
if str(CORE_SRC) not in sys.path:
    sys.path.insert(0, str(CORE_SRC))

_worker_env = os.environ.get("MV_WORKER_ENV", ".worker-seamless")
if not _worker_env.startswith(".envs/"):
    _worker_env = f".envs/{_worker_env.removeprefix('.')}"

read_env_files(
    ROOT_DIR,
    ".envs/.worker",
    ".envs/.db",
    ".envs/.broker",
    ".envs/.s3",
    _worker_env,
    ".env",
)

env = environ.Env(DEBUG=(bool, True))

SECRET_KEY = env("DJANGO_SECRET_KEY", default="dev-insecure-change-me")
DEBUG = env("DEBUG", default=True)

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django_celery_results",
    "languages",
    "translation_models",
    "video",
]

MIDDLEWARE = []

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgres://mv:mv@localhost:5432/multilingual_videos",
    )
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="amqp://guest:guest@localhost:5672//")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="django-db")
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 60 * 60 * 2
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_IMPORTS = ("tasks.video",)

# Per-worker .env (.worker-seamless / .worker-zeroshot / .worker-zeroswot)
WORKER_ENABLED = env.bool("WORKER_ENABLED", default=True)

YANDEX_S3_ACCESS_KEY_ID = env("YANDEX_S3_ACCESS_KEY_ID", default="")
YANDEX_S3_SECRET_ACCESS_KEY = env("YANDEX_S3_SECRET_ACCESS_KEY", default="")
YANDEX_S3_ENDPOINT = env("YANDEX_S3_ENDPOINT", default="https://storage.yandexcloud.net")
YANDEX_S3_REGION = env("YANDEX_S3_REGION", default="ru-central1")
YANDEX_S3_BUCKET_UPLOADS = env("YANDEX_S3_BUCKET_UPLOADS", default="multilingual-vids")
YANDEX_S3_BUCKET_RESULTS = env("YANDEX_S3_BUCKET_RESULTS", default="multilingual-vids")
YANDEX_S3_BUCKET_TEMP = env("YANDEX_S3_BUCKET_TEMP", default="multilingual-vids")

ZEROSHOT_MT_S3_PREFIX = env("ZEROSHOT_MT_S3_PREFIX", default="models/zeroshot/trained_8")
ZEROSHOT_MT_S3_BUCKET = env("ZEROSHOT_MT_S3_BUCKET", default="")
ZEROSHOT_WHISPER_MODEL = env("ZEROSHOT_WHISPER_MODEL", default="large-v3")
ZEROSHOT_WHISPER_DEVICE = env("ZEROSHOT_WHISPER_DEVICE", default="cpu")
ZEROSHOT_WHISPER_COMPUTE_TYPE = env("ZEROSHOT_WHISPER_COMPUTE_TYPE", default="int8")
ZEROSHOT_TTS_VOICE = env("ZEROSHOT_TTS_VOICE", default="uk-UA-OstapNeural")

SEAMLESS_HF_MODEL_ID = env(
    "SEAMLESS_HF_MODEL_ID",
    default="facebook/hf-seamless-m4t-medium",
)
SEAMLESS_MODEL_LOCAL_DIR = env("SEAMLESS_MODEL_LOCAL_DIR", default="")
SEAMLESS_DEVICE = env("SEAMLESS_DEVICE", default="auto")
SEAMLESS_MAX_NEW_TOKENS = env.int("SEAMLESS_MAX_NEW_TOKENS", default=0)
# Long audio: translate in chunks (seconds). 0 = single pass (often truncates ~8–10s output).
SEAMLESS_CHUNK_MAX_SECONDS = env.float("SEAMLESS_CHUNK_MAX_SECONDS", default=5.0)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json_message": {"format": "%(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "json_message"},
    },
    "loggers": {
        "config.celery": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "tasks": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "flow": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "flow.seamless": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "huggingface_hub": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "transformers": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
}
