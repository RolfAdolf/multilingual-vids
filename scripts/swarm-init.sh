#!/usr/bin/env sh
# Initialize Docker Swarm and label nodes for multilingual-vids stack.
# Run on the manager (first) node. Re-run swarm-label-node.sh on workers after join.
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! docker info >/dev/null 2>&1; then
  echo "Docker is not available." >&2
  exit 1
fi

if ! docker info 2>/dev/null | grep -q "Swarm: active"; then
  echo "Initializing swarm..."
  docker swarm init
else
  echo "Swarm already active."
fi

MANAGER_ID="$(docker node ls --filter role=manager -q | head -n1)"
if [ -z "$MANAGER_ID" ]; then
  echo "No manager node found." >&2
  exit 1
fi

echo "Labeling manager node ${MANAGER_ID} (db, edge; gpu if nvidia-smi works)..."
docker node update --label-add db=true "$MANAGER_ID"
docker node update --label-add edge=true "$MANAGER_ID"

if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi >/dev/null 2>&1; then
  docker node update --label-add gpu=true "$MANAGER_ID"
  echo "GPU label set on manager."
else
  echo "nvidia-smi not available — skip gpu label on manager (set manually on GPU nodes)."
fi

echo ""
echo "Swarm ready. Join workers with:"
docker swarm join-token worker 2>/dev/null | sed -n '2p' || true
echo ""
echo "On each GPU worker after join:"
echo "  ./scripts/swarm-label-node.sh <NODE_ID> gpu"
echo "On a dedicated DB host:"
echo "  ./scripts/swarm-label-node.sh <NODE_ID> db"
echo ""
echo "Next: cp .envs_examples/* .envs/, build images, ./scripts/swarm-deploy.sh"
