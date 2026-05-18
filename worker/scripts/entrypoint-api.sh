#!/bin/sh
set -e

cd /app/worker/src
python manage.py migrate --noinput
exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers "${GUNICORN_WORKERS:-2}"
