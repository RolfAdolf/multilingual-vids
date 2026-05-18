#!/bin/sh
set -e

cd /app/worker/src
python manage.py migrate --noinput

exec celery -A config worker \
  --loglevel="${CELERY_LOGLEVEL:-info}" \
  -Q "${CELERY_QUEUE:?CELERY_QUEUE is required}" \
  -c "${CELERY_CONCURRENCY:-1}"
