FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VERSION=1.8.3 \
    POETRY_VIRTUALENVS_CREATE=false \
    PYTHONPATH=/app/worker/src:/app/core-api/src \
    CORE_SRC_PATH=/app/core-api/src

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir "poetry==${POETRY_VERSION}"

COPY worker/pyproject.toml worker/poetry.lock /app/worker/
WORKDIR /app/worker

ARG POETRY_GROUP=
ARG INSTALL_DEV=false
RUN poetry install --no-interaction --no-ansi --no-root \
    && if [ -n "$POETRY_GROUP" ]; then poetry install --no-interaction --no-ansi --with "$POETRY_GROUP"; fi \
    && if [ "$INSTALL_DEV" = "true" ]; then poetry install --no-interaction --no-ansi --with dev; fi

COPY core-api/src /app/core-api/src
COPY worker/src /app/worker/src
COPY worker/scripts/entrypoint-celery.sh /app/worker/scripts/entrypoint-celery.sh
COPY worker/scripts/entrypoint-celery-dev.sh /app/worker/scripts/entrypoint-celery-dev.sh
RUN chmod +x /app/worker/scripts/entrypoint-celery.sh /app/worker/scripts/entrypoint-celery-dev.sh

ENTRYPOINT ["/app/worker/scripts/entrypoint-celery.sh"]
