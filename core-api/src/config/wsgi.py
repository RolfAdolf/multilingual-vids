import os
from pathlib import Path
import sys

src = Path(__file__).resolve().parent.parent
if str(src) not in sys.path:
    sys.path.insert(0, str(src))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
