# Multilingual Videos

**core-api** — единственный HTTP API (языки, модели, видео, admin).  
**worker-*** — только Celery consumers и ML-пайплайны (`flow/*`).

## Структура

```
multilingual-vids/
  core-api/src/     # Django API, video, storage, translation_models
  worker/src/       # Celery tasks, flow/* (без HTTP)
  frontend/
  .envs_examples/
  docker-compose.yaml
```

## Env-файлы

```bash
mkdir -p .envs
cp .envs_examples/.db .envs/.db
cp .envs_examples/.broker .envs/.broker
cp .envs_examples/.s3 .envs/.s3
cp .envs_examples/.core-api .envs/.core-api
cp .envs_examples/.worker .envs/.worker
cp .envs_examples/.worker-seamless .envs/.worker-seamless
cp .envs_examples/.worker-zeroswot .envs/.worker-zeroswot
cp .envs_examples/.worker-zeroshot .envs/.worker-zeroshot
cp .envs_examples/.frontend frontend/.env
```

Воркеры в Compose: `.worker` (общее + хосты `postgres` / `rabbitmq`) + файл очереди. Локальный Celery: те же файлы, но `.db` и `.broker` переопределяют URL на `localhost`.

## Docker Compose

| Сервис | Очередь | Образ | Роль |
|--------|---------|-------|------|
| `core-api` | — | `core-api/Dockerfile` | gunicorn, `/api/v1/*` |
| `worker-seamless` | `seamless` | `worker/Dockerfile.gpu` | SeamlessM4T S2ST (CUDA) |
| `worker-zeroswot` | `zeroswot` | `worker/Dockerfile.gpu` | ZeroSwot (CUDA) |
| `worker-zeroshot` | `zeroshot` | `worker/Dockerfile.gpu` | Whisper + MT + TTS (CUDA) |

### Production (GPU-сервер)

На хосте: [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html), `nvidia-smi` работает.

```bash
cp .envs_examples/.deploy .envs/.deploy

set -a && source .envs/.deploy && set +a
docker compose -f docker-compose.yaml -f docker-compose.gpu.yaml up -d --build
# или: ./scripts/compose-prod.sh up -d --build
```

### Production (Docker Swarm)

Кластер из нескольких нод или один manager с labels `db`, `gpu`, `edge`. Подробно: [infra/swarm/README.md](infra/swarm/README.md).

```bash
cp .envs_examples/* .envs/
cp infra/swarm/env/stack.env.example infra/swarm/env/stack.env

chmod +x scripts/swarm-*.sh
./scripts/swarm-init.sh
./scripts/swarm-build-images.sh
./scripts/swarm-deploy.sh              # + stack.gpu.yaml
./scripts/swarm-deploy.sh --with-ops   # опционально Flower :5555
```

Образы нужно собрать **до** `stack deploy` (в stack-файлах нет `build:`). Обновление: новый `IMAGE_TAG` → `swarm-build-images.sh` → `swarm-deploy.sh`.

- Снаружи открыт только **nginx** (`HTTP_PORT`, по умолчанию 80).
- Postgres / RabbitMQ / Redis — только внутри сети Compose.
- Кэш Hugging Face / PyTorch: volumes `hf_cache`, `torch_cache`.
- GPU: `gpus: all` на ML-воркерах, `CELERY_CONCURRENCY=1`, `SEAMLESS_DEVICE=cuda`.
- Flower (только localhost): `docker compose --profile ops up -d flower`
- SeamlessM4T: перед стартом загрузить модель на host в `SEAMLESS_HOST_MODEL_DIR` (по умолчанию `/opt/models/seamless-m4t-v2-large`). `worker-seamless` монтирует её read-only в `/models/seamless-m4t-v2-large` и грузит через `transformers.from_pretrained()` без обращения к Hugging Face. Локальную копию можно подготовить командой `python scripts/download-hf-model.py facebook/seamless-m4t-v2-large --output-dir models/seamless-m4t-v2-large`.
- Zeroshot MT: при старте `worker-zeroshot` скачивает SavedModel из S3 (`ZEROSHOT_MT_S3_PREFIX`, по умолчанию `models/zeroshot/trained_8`), грузит в память и удаляет temp-директорию

### Локальная разработка (без GPU)

CPU-образ `worker/Dockerfile`, bind-mount исходников, hot reload:

```bash
# dev-файл только дополняет базовый docker-compose.yaml
docker compose -f docker-compose.yaml -f docker-compose.dev.yaml up --build

# или
./scripts/compose-dev.sh up --build
```

| Сервис | Механизм |
|--------|----------|
| `core-api` | `runserver` |
| `frontend` | Vite HMR `:5173` |
| `worker-*` | `entrypoint-celery-dev.sh` |

Отключить воркер без остановки контейнера (не грузит ML, задачи → `ERROR` в БД): в `.envs/.worker-seamless`, `.worker-zeroshot` или `.worker-zeroswot` задать `WORKER_ENABLED=false`.

Порты для отладки: Postgres `5432`, RabbitMQ `5672`/`15672`, Redis `6379`, Vite `5173`.

### Presigned upload из браузера (CORS)

Прямой `PUT` на Yandex Object Storage с `http://localhost` требует CORS на бакете. Один раз после создания бакета:

```bash
docker compose exec core-api python manage.py configure_s3_cors
```

В консоли Yandex Cloud: бакет → **Безопасность** → **CORS** — те же origins, что в `S3_CORS_ALLOWED_ORIGINS` (`.envs/.s3`).

### Django Admin

URL: `http://<хост>/admin/` (через nginx в prod).

**Готового логина/пароля в репозитории нет** — один раз создай суперпользователя:

```bash
docker compose exec core-api python manage.py createsuperuser
```

(или `./scripts/compose-prod.sh exec core-api python manage.py createsuperuser` на GPU-сервере)

Статика админки (`DEBUG=false`): WhiteNoise + `collectstatic` при старте `core-api`. После обновления пересобери `core-api` и `nginx`.

## Локально (Python 3.10)

**API:**

```bash
cd core-api && poetry install
cd src && poetry run python manage.py migrate
poetry run gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

**Celery worker:**

```bash
cd worker && poetry install --with seamless
export CORE_SRC_PATH=../core-api/src
export MV_WORKER_ENV=worker-seamless
cd src && poetry run celery -A config worker -Q seamless
```

Обучение MT: `../diploma/scripts/train_zeroshot_mt.py`.

## Тесты (core-api)

```bash
cd core-api && poetry install --with dev && poetry run pytest
```

SQLite in-memory, без Postgres/S3 (см. `src/config/settings_test.py`).
