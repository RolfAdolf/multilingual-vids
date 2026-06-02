#!/usr/bin/env sh
# Apply placement labels to a swarm node.
# Usage: ./scripts/swarm-label-node.sh <node_id|hostname> [db] [gpu] [edge]
set -e

if [ $# -lt 2 ]; then
  echo "Usage: $0 <node_id|hostname> [db] [gpu] [edge]" >&2
  echo "Example: $0 worker-gpu-1 gpu" >&2
  exit 1
fi

NODE="$1"
shift

for label in "$@"; do
  case "$label" in
    db|gpu|edge)
      echo "Setting label ${label}=true on node ${NODE}"
      docker node update --label-add "${label}=true" "$NODE"
      ;;
    *)
      echo "Unknown label: ${label} (use db, gpu, or edge)" >&2
      exit 1
      ;;
  esac
done

docker node inspect "$NODE" --format '{{ .Description.Hostname }}: {{ .Spec.Labels }}'
