# Docker Swarm — Multilingual Videos

Развёртывание production-стека через **Docker Swarm** (в отличие от `docker compose` на одном хосте).

| Файл | Назначение |
|------|------------|
| `stack.yml` | Основной стек (Postgres, RabbitMQ, Redis, API, workers, frontend, nginx) |
| `stack.gpu.yml` | GPU-воркеры: bind-mount Seamless, `generic_resources` GPU |
| `stack.ops.yml` | Опционально: Flower на порту 5555 |
| `env/stack.env` | Теги образов, порты, имя стека |

Скрипты в `scripts/`: `swarm-init.sh`, `swarm-label-node.sh`, `swarm-build-images.sh`, `swarm-deploy.sh`, `swarm-remove.sh`.

## Требования

- Docker Engine 24+ с поддержкой Swarm
- На GPU-нодах: [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html), `nvidia-smi`
- Для Swarm GPU: на нодах должен быть настроен advertising GPU (см. [NVIDIA Swarm](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/docker-swarm.html)) — иначе используйте одну GPU-ноду и label `gpu=true`

## Быстрый старт (одна нода)

```bash
mkdir -p .envs
cp .envs_examples/* .envs/
cp infra/swarm/env/stack.env.example infra/swarm/env/stack.env
# отредактируйте .envs/.core-api, .envs/.s3, пароли в .envs/.db

chmod +x scripts/swarm-*.sh
./scripts/swarm-init.sh          # swarm init + labels db, edge, gpu
./scripts/swarm-build-images.sh
./scripts/swarm-deploy.sh
```

Проверка:

```bash
docker stack services multilingual-vids
docker service logs multilingual-vids_core-api -f
curl -s http://localhost/health
```

Админ: `docker exec -it $(docker ps -q -f name=multilingual-vids_core-api) python manage.py createsuperuser`  
(имя контейнера может отличаться — смотрите `docker ps`).

## Топология нод (несколько серверов)

| Label | Сервисы |
|-------|---------|
| `db=true` | postgres, rabbitmq, redis |
| `gpu=true` | worker-seamless, worker-zeroswot, worker-zeroshot |
| `edge=true` | nginx (порт 80, `mode: host`) |

```bash
# После docker swarm join на воркере:
docker node ls
./scripts/swarm-label-node.sh <NODE_ID> gpu
./scripts/swarm-label-node.sh <NODE_ID> db
```

На manager обычно: `db` + `edge`. Seamless-модель (`SEAMLESS_HOST_MODEL_DIR`) должна лежать **на той же ноде**, где запускается `worker-seamless`.

## Образы и registry

Swarm **не собирает** образы из `build:` — только `image:`.

```bash
./scripts/swarm-build-images.sh
# опционально push:
export IMAGE_PREFIX=registry.example.com/mv/
export IMAGE_TAG=v1.0.0
./scripts/swarm-build-images.sh
docker push registry.example.com/mv/core-api:v1.0.0
# ... остальные образы
./scripts/swarm-deploy.sh
```

Переменные: `IMAGE_PREFIX`, `IMAGE_TAG` в `infra/swarm/env/stack.env`.

## Обновление стека

```bash
export IMAGE_TAG=v1.0.1
./scripts/swarm-build-images.sh
./scripts/swarm-deploy.sh   # rolling update по update_config
```

## Flower (мониторинг Celery)

```bash
./scripts/swarm-deploy.sh --with-ops
# http://<manager-host>:5555
```

## Отличия от docker compose

| Compose | Swarm |
|---------|-------|
| `build:` в compose | Сборка через `swarm-build-images.sh` |
| `depends_on` | Порядок через healthcheck + restart |
| `restart: unless-stopped` | `deploy.restart_policy` |
| GPU `devices` | `stack.gpu.yml` + `generic_resources` |
| Один хост | Overlay-сеть, placement labels |

## Удаление

```bash
./scripts/swarm-remove.sh
# volumes: docker volume ls | grep multilingual
```

## Секреты (опционально)

Для production можно вынести пароли в Swarm secrets и подключить в `stack.yml` вместо `env_file`. Пример создания:

```bash
echo -n "strong-password" | docker secret create mv_postgres_password -
```

Дальше — смонтировать secret в `postgres` / `core-api` (см. [Docker secrets](https://docs.docker.com/engine/swarm/secrets/)).
