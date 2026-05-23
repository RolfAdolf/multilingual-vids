#!/bin/sh
set -e

cd /app/worker/src

echo "{\"event\":\"worker.process.start\",\"layer\":\"worker\",\"queue\":\"${CELERY_QUEUE}\"}"

exec celery -A config worker \
  --loglevel="${CELERY_LOGLEVEL:-info}" \
  -Q "${CELERY_QUEUE:?CELERY_QUEUE is required}" \
  -c "${CELERY_CONCURRENCY:-1}"
