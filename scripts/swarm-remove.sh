#!/usr/bin/env sh
# Remove multilingual-vids swarm stack (volumes are kept).
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

STACK_ENV="${ROOT}/infra/swarm/env/stack.env"
if [ -f "$STACK_ENV" ]; then
  # shellcheck disable=SC1090
  set -a && . "$STACK_ENV" && set +a
fi

STACK_NAME="${STACK_NAME:-multilingual-vids}"

echo "Removing stack ${STACK_NAME}..."
docker stack rm "$STACK_NAME"

echo "Waiting for services to drain..."
sleep 5
docker stack ls

echo "Named volumes (pg_data, hf_cache, ...) are not removed automatically."
