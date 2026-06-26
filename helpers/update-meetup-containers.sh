#!/usr/bin/env bash
set -Eeuo pipefail

# Usage:
#   ./update-meetup-containers.sh          # pulls and starts :latest
#   ./update-meetup-containers.sh v1.2.3   # pulls and starts a specific Docker Hub tag

TAG="${1:-latest}"

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
BACKEND_SERVICE="${BACKEND_SERVICE:-backend}"
FRONTEND_SERVICE="${FRONTEND_SERVICE:-frontend}"
DB_SERVICE="${DB_SERVICE:-db}"

BACKEND_IMAGE="${BACKEND_IMAGE:-msj102/meetup-helper-backend}"
FRONTEND_IMAGE="${FRONTEND_IMAGE:-msj102/meetup-helper-frontend}"

if [[ ! "$TAG" =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "Invalid Docker image tag: $TAG" >&2
  exit 1
fi

if [[ ! -f "$COMPOSE_FILE" ]]; then
  echo "Compose file not found: $COMPOSE_FILE" >&2
  exit 1
fi

if docker compose version >/dev/null 2>&1; then
  COMPOSE=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE=(docker-compose)
else
  echo "Docker Compose was not found. Install Docker Compose first." >&2
  exit 1
fi

OVERRIDE_FILE="$(mktemp)"
trap 'rm -f "$OVERRIDE_FILE"' EXIT

cat > "$OVERRIDE_FILE" <<EOF
services:
  ${BACKEND_SERVICE}:
    image: ${BACKEND_IMAGE}:${TAG}
  ${FRONTEND_SERVICE}:
    image: ${FRONTEND_IMAGE}:${TAG}
EOF

COMPOSE_CMD=("${COMPOSE[@]}" -f "$COMPOSE_FILE" -f "$OVERRIDE_FILE")

wait_for_service_health() {
  local service="$1"
  local container_id
  local status

  container_id="$("${COMPOSE_CMD[@]}" ps -q "$service" 2>/dev/null || true)"
  if [[ -z "$container_id" ]]; then
    return 0
  fi

  status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$container_id")"
  if [[ "$status" == "none" ]]; then
    return 0
  fi

  echo "Waiting for ${service} to become healthy..."
  for _ in {1..60}; do
    status="$(docker inspect --format '{{.State.Health.Status}}' "$container_id")"
    if [[ "$status" == "healthy" ]]; then
      return 0
    fi
    sleep 2
  done

  echo "Service ${service} did not become healthy in time." >&2
  return 1
}

echo "Pulling images from Docker Hub:"
echo "  ${BACKEND_IMAGE}:${TAG}"
echo "  ${FRONTEND_IMAGE}:${TAG}"
"${COMPOSE_CMD[@]}" pull "$BACKEND_SERVICE" "$FRONTEND_SERVICE"

if "${COMPOSE_CMD[@]}" config --services | grep -qx "$DB_SERVICE"; then
  echo "Ensuring database service is running..."
  "${COMPOSE_CMD[@]}" up -d "$DB_SERVICE"
  wait_for_service_health "$DB_SERVICE"
fi

echo "Recreating backend and frontend with tag: ${TAG}"
"${COMPOSE_CMD[@]}" up -d --no-deps --force-recreate "$BACKEND_SERVICE" "$FRONTEND_SERVICE"

echo
echo "Current status:"
"${COMPOSE_CMD[@]}" ps "$BACKEND_SERVICE" "$FRONTEND_SERVICE"
