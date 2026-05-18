# Multilingual Videos

**core-api** (каталог) + **worker-api** (видео HTTP) + **3 Celery-воркера** (по одной ML-модели).

## Структура

```
multilingual-vids/
  core-api/
  worker/              # код API + flow/*; образы различаются POETRY_GROUP
  frontend/
  .envs_examples/      # шаблоны env по сервисам
  docker-compose.yaml
```

## Env-файлы

```bash
mkdir -p .envs
cp .envs_examples/.db.example .envs/.db
cp .envs_examples/.broker.example .envs/.broker
cp .envs_examples/.s3.example .envs/.s3
cp .envs_examples/.core-api.example .envs/.core-api
cp .envs_examples/.worker-api.example .envs/.worker-api
cp .envs_examples/.worker-seamless.example .envs/.worker-seamless
cp .envs_examples/.worker-zeroswot.example .envs/.worker-zeroswot
cp .envs_examples/.worker-zeroshot.example .envs/.worker-zeroshot
cp .envs_examples/.frontend.example frontend/.env
# YANDEX_S3_* → .envs/.s3
```

## Docker Compose

| Сервис | Очередь | Poetry group | Роль |
|--------|---------|--------------|------|
| `worker-api` | — | (базовые deps) | gunicorn, `/api/v1/videos` |
| `worker-seamless` | `seamless` | `seamless` | Celery consumer |
| `worker-zeroswot` | `zeroswot` | `zeroswot` | Celery consumer |
| `worker-zeroshot` | `zeroshot` | `zeroshot` | Celery consumer |

```bash
docker compose up --build
```

Flower: `docker compose --profile ops up flower`

## Локально (Python 3.10.6)

```bash
cd worker && python3.10 -m venv .venv && poetry env use .venv/bin/python
poetry install --with seamless   # или zeroswot / zeroshot

cd src
export CORE_SRC_PATH=../../core-api/src
export MV_WORKER_ENV=worker-seamless   # или worker-api, worker-zeroshot, …
poetry run celery -A config worker -Q seamless
```

Обучение MT: `../diploma/scripts/train_zeroshot_mt.py`.
