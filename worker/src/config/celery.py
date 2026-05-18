import os
import sys
from pathlib import Path

from celery import Celery

src = Path(__file__).resolve().parent.parent
if str(src) not in sys.path:
    sys.path.insert(0, str(src))

root = src.parent.parent
core_src = Path(os.environ.get("CORE_SRC_PATH", root / "core-api" / "src")).resolve()
if core_src.is_dir() and str(core_src) not in sys.path:
    sys.path.insert(0, str(core_src))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("worker")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
