#!/bin/sh
set -e

cd /app/worker/src

run_worker() {
  exec celery -A config worker \
    --loglevel="${CELERY_LOGLEVEL:-info}" \
    -Q "${CELERY_QUEUE:?CELERY_QUEUE is required}" \
    -c "${CELERY_CONCURRENCY:-1}"
}

if [ "${CELERY_DEV_RELOAD:-0}" = "1" ]; then
  exec watchmedo auto-restart \
    --directory=/app/worker/src \
    --directory=/app/core-api/src \
    --pattern='*.py' \
    --recursive \
    --signal=SIGTERM \
    -- celery -A config worker \
      --loglevel="${CELERY_LOGLEVEL:-info}" \
      -Q "${CELERY_QUEUE:?CELERY_QUEUE is required}" \
      -c "${CELERY_CONCURRENCY:-1}"
fi

run_worker
