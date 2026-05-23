#!/usr/bin/env sh
set -e
cd "$(dirname "$0")/.."
exec docker compose -f docker-compose.yaml -f docker-compose.gpu.yaml "$@"
