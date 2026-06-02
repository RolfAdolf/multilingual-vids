#!/usr/bin/env sh
# Deploy multilingual-vids stack to Docker Swarm.
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

WITH_OPS=false
WITH_GPU=true
DEPLOY_ARGS=""

while [ $# -gt 0 ]; do
  case "$1" in
    --with-ops)
      WITH_OPS=true
      shift
      ;;
    --no-gpu)
      WITH_GPU=false
      shift
      ;;
    -h|--help)
      echo "Usage: $0 [--with-ops] [--no-gpu] [extra docker stack deploy args...]"
      exit 0
      ;;
    *)
      DEPLOY_ARGS="$DEPLOY_ARGS $1"
      shift
      ;;
  esac
done

for f in .envs/.db .envs/.broker .envs/.s3 .envs/.core-api .envs/.worker; do
  if [ ! -f "$f" ]; then
    echo "Missing $f — copy from .envs_examples/ first." >&2
    exit 1
  fi
done

STACK_ENV="${ROOT}/infra/swarm/env/stack.env"
if [ -f "$STACK_ENV" ]; then
  # shellcheck disable=SC1090
  set -a && . "$STACK_ENV" && set +a
fi

if [ -f "${ROOT}/.envs/.deploy" ]; then
  # shellcheck disable=SC1090
  set -a && . "${ROOT}/.envs/.deploy" && set +a
fi

STACK_NAME="${STACK_NAME:-multilingual-vids}"

COMPOSE_FILES="-c infra/swarm/stack.yml"
if [ "$WITH_GPU" = true ]; then
  COMPOSE_FILES="$COMPOSE_FILES -c infra/swarm/stack.gpu.yml"
fi
if [ "$WITH_OPS" = true ]; then
  COMPOSE_FILES="$COMPOSE_FILES -c infra/swarm/stack.ops.yml"
fi

echo "Deploying stack '${STACK_NAME}' (gpu=${WITH_GPU}, ops=${WITH_OPS})..."
# shellcheck disable=SC2086
exec docker stack deploy $COMPOSE_FILES --with-registry-auth "$STACK_NAME" $DEPLOY_ARGS
