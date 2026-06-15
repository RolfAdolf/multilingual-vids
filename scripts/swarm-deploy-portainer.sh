#!/usr/bin/env sh
# Deploy Portainer CE for Swarm cluster monitoring (separate stack: portainer).
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! docker info 2>/dev/null | grep -q "Swarm: active"; then
  echo "Swarm is not active. Run ./scripts/swarm-init.sh first." >&2
  exit 1
fi

STACK_ENV="${ROOT}/infra/swarm/env/stack.env"
if [ -f "$STACK_ENV" ]; then
  # shellcheck disable=SC1090
  set -a && . "$STACK_ENV" && set +a
fi

PORTAINER_STACK="${PORTAINER_STACK_NAME:-portainer}"
HTTP_PORT="${PORTAINER_HTTP_PORT:-9000}"
HTTPS_PORT="${PORTAINER_HTTPS_PORT:-9443}"

echo "Deploying Portainer stack '${PORTAINER_STACK}' (HTTP ${HTTP_PORT}, HTTPS ${HTTPS_PORT})..."
docker stack deploy -c infra/swarm/stack.portainer.yml "$PORTAINER_STACK"

echo ""
echo "Portainer UI (on swarm manager node):"
echo "  http://<manager>:${HTTP_PORT}"
echo "  https://<manager>:${HTTPS_PORT}  (recommended)"
echo ""
echo "On first login create an admin user, then Environment → Get Started (local Swarm)."
echo "Your app stack appears under Stacks → ${STACK_NAME:-multilingual-vids}."
