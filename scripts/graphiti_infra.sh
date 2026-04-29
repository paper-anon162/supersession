#!/usr/bin/env bash
# Helper to bring up / tear down / inspect the FalkorDB stack used by the
# Graphiti baseline. See docker/docker-compose.graphiti.yml for the
# service definition.
#
# Usage:
#   scripts/graphiti_infra.sh up       # docker compose up -d + healthcheck
#   scripts/graphiti_infra.sh down     # docker compose down (data preserved)
#   scripts/graphiti_infra.sh wipe     # docker compose down -v (delete volume)
#   scripts/graphiti_infra.sh status   # ps + healthcheck output
#   scripts/graphiti_infra.sh logs     # tail container logs
#   scripts/graphiti_infra.sh ping     # redis-cli -p 6379 ping
#
# Exit codes:
#   0  ok
#   1  bad subcommand / missing dependency / ping failed
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${REPO_ROOT}/docker/docker-compose.graphiti.yml"

if ! command -v docker >/dev/null 2>&1; then
  echo "[graphiti_infra] docker not found on PATH" >&2
  exit 1
fi

# Prefer `docker compose` (v2 plugin); fall back to `docker-compose`.
if docker compose version >/dev/null 2>&1; then
  COMPOSE=(docker compose -f "$COMPOSE_FILE")
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE=(docker-compose -f "$COMPOSE_FILE")
else
  echo "[graphiti_infra] neither 'docker compose' nor 'docker-compose' is installed" >&2
  exit 1
fi

cmd="${1:-status}"

case "$cmd" in
  up)
    "${COMPOSE[@]}" up -d
    echo "[graphiti_infra] waiting for FalkorDB to become healthy..."
    # Poll the healthcheck status for up to ~30s.
    for i in $(seq 1 30); do
      status=$(docker inspect --format '{{.State.Health.Status}}' ssbench-falkordb 2>/dev/null || echo unknown)
      if [[ "$status" == "healthy" ]]; then
        echo "[graphiti_infra] FalkorDB is healthy."
        break
      fi
      sleep 1
    done
    if command -v redis-cli >/dev/null 2>&1; then
      echo -n "[graphiti_infra] redis-cli -p 6379 ping → "
      redis-cli -p 6379 ping || true
    else
      echo "[graphiti_infra] (redis-cli not installed; skipping ping check)"
    fi
    ;;
  down)
    "${COMPOSE[@]}" down
    ;;
  wipe)
    "${COMPOSE[@]}" down -v
    ;;
  status)
    "${COMPOSE[@]}" ps
    docker inspect --format 'health: {{.State.Health.Status}}' ssbench-falkordb 2>/dev/null || true
    ;;
  logs)
    "${COMPOSE[@]}" logs --tail=200 -f
    ;;
  ping)
    if ! command -v redis-cli >/dev/null 2>&1; then
      echo "[graphiti_infra] redis-cli not installed" >&2
      exit 1
    fi
    redis-cli -p 6379 ping
    ;;
  *)
    echo "Usage: $0 {up|down|wipe|status|logs|ping}" >&2
    exit 1
    ;;
esac
