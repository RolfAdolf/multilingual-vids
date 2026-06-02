#!/usr/bin/env sh
# Build and tag images for Docker Swarm (no build: in stack files).
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

STACK_ENV="${ROOT}/infra/swarm/env/stack.env"
if [ -f "$STACK_ENV" ]; then
  # shellcheck disable=SC1090
  set -a && . "$STACK_ENV" && set +a
fi

PREFIX="${IMAGE_PREFIX:-multilingual-vids/}"
TAG="${IMAGE_TAG:-latest}"

# Normalize prefix: ensure trailing slash when non-empty and not already present
case "$PREFIX" in
  */) ;;
  "") ;;
  *) PREFIX="${PREFIX}/" ;;
esac

echo "Building images with prefix=${PREFIX} tag=${TAG}"

docker build -f core-api/Dockerfile -t "${PREFIX}core-api:${TAG}" .

docker build -f worker/Dockerfile.gpu \
  --build-arg POETRY_GROUP=seamless \
  -t "${PREFIX}worker-seamless:${TAG}" .

docker build -f worker/Dockerfile.gpu \
  --build-arg POETRY_GROUP=zeroswot \
  -t "${PREFIX}worker-zeroswot:${TAG}" .

docker build -f worker/Dockerfile.gpu \
  --build-arg POETRY_GROUP=zeroshot \
  -t "${PREFIX}worker-zeroshot:${TAG}" .

docker build -f worker/Dockerfile -t "${PREFIX}worker-cpu:${TAG}" .

docker build -f frontend/Dockerfile \
  --build-arg VITE_API_BASE_URL=/api/v1 \
  -t "${PREFIX}frontend:${TAG}" .

echo "Done. Push to registry if needed:"
echo "  export REGISTRY=registry.example.com/mv"
echo "  for img in core-api worker-seamless worker-zeroswot worker-zeroshot worker-cpu frontend; do"
echo "    docker tag ${PREFIX}\$img:${TAG} \${REGISTRY}/\$img:${TAG}"
echo "    docker push \${REGISTRY}/\$img:${TAG}"
echo "  done"
