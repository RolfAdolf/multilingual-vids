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

_worker_env = os.environ.get("MV_WORKER_ENV", ".worker-api")
if not _worker_env.startswith(".envs/"):
    _worker_env = f".envs/{_worker_env.removeprefix('.')}"

read_env_files(
    ROOT_DIR,
    ".envs/.db",
    ".envs/.broker",
    ".envs/.s3",
    _worker_env,
    ".env",
)

env = environ.Env(
    DEBUG=(bool, True),
    ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1", "worker"]),
    CORS_ALLOWED_ORIGINS=(list, ["http://localhost", "http://localhost:5173"]),
)

SECRET_KEY = env("DJANGO_SECRET_KEY", default="dev-insecure-change-me")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "drf_spectacular",
    "django_celery_results",
    "translation_models",
    "languages",
    "video",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "config.middleware.RequestIdMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgres://mv:mv@localhost:5432/multilingual_videos",
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ALLOWED_ORIGINS = env("CORS_ALLOWED_ORIGINS")
CORS_ALLOW_CREDENTIALS = True

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Multilingual Videos — Worker API",
    "VERSION": "1.0.0",
}

CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="amqp://guest:guest@localhost:5672//")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="django-db")
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 60 * 60 * 2
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"

REDIS_URL = env("REDIS_URL", default="redis://localhost:6379/0")

YANDEX_S3_ACCESS_KEY_ID = env("YANDEX_S3_ACCESS_KEY_ID", default="")
YANDEX_S3_SECRET_ACCESS_KEY = env("YANDEX_S3_SECRET_ACCESS_KEY", default="")
YANDEX_S3_ENDPOINT = env("YANDEX_S3_ENDPOINT", default="https://storage.yandexcloud.net")
YANDEX_S3_REGION = env("YANDEX_S3_REGION", default="ru-central1")
YANDEX_S3_BUCKET_UPLOADS = env("YANDEX_S3_BUCKET_UPLOADS", default="multilingual-vids")
YANDEX_S3_BUCKET_RESULTS = env("YANDEX_S3_BUCKET_RESULTS", default="multilingual-vids")
YANDEX_S3_BUCKET_TEMP = env("YANDEX_S3_BUCKET_TEMP", default="multilingual-vids")

S3_PRESIGNED_TTL_SECONDS = env.int("S3_PRESIGNED_TTL_SECONDS", default=900)
MAX_UPLOAD_BYTES = env.int("MAX_UPLOAD_BYTES", default=500 * 1024 * 1024)
ALLOWED_VIDEO_CONTENT_TYPES = (
    "video/mp4",
    "video/webm",
    "video/quicktime",
    "video/x-matroska",
)
ALLOW_MULTIPART_UPLOAD = env.bool("ALLOW_MULTIPART_UPLOAD", default=False)

ZEROSHOT_GRADUATE_PROJECT_DIR = env("ZEROSHOT_GRADUATE_PROJECT_DIR", default="")
ZEROSHOT_MT_TRANSLATOR_PATH = env("ZEROSHOT_MT_TRANSLATOR_PATH", default="")
ZEROSHOT_MT_EXPORT_DIR = env("ZEROSHOT_MT_EXPORT_DIR", default="trained_models/augmented")
ZEROSHOT_MT_EPOCH = env.int("ZEROSHOT_MT_EPOCH", default=8)
ZEROSHOT_WHISPER_MODEL = env("ZEROSHOT_WHISPER_MODEL", default="large-v3")
ZEROSHOT_WHISPER_DEVICE = env("ZEROSHOT_WHISPER_DEVICE", default="cpu")
ZEROSHOT_WHISPER_COMPUTE_TYPE = env("ZEROSHOT_WHISPER_COMPUTE_TYPE", default="int8")
ZEROSHOT_TTS_VOICE = env("ZEROSHOT_TTS_VOICE", default="uk-UA-OstapNeural")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "%(levelname)s %(asctime)s %(name)s %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
}
