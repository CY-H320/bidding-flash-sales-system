#!/usr/bin/env bash
set -euo pipefail

APP_IMAGE=${APP_IMAGE:-bidding-api:latest}
ENV_FILE=${ENV_FILE:-/opt/bidding/.env}
CONTAINER_NAME=${CONTAINER_NAME:-bidding-api}
HOST_PORT=${HOST_PORT:-8000}

if [ ! -f "$ENV_FILE" ]; then
  echo "Environment file $ENV_FILE not found" >&2
  exit 1
fi

echo "Pulling image $APP_IMAGE"
docker pull "$APP_IMAGE"

echo "Stopping existing container if present"
docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true

echo "Starting container $CONTAINER_NAME on port ${HOST_PORT}"
docker run -d \
  --name "$CONTAINER_NAME" \
  --env-file "$ENV_FILE" \
  -p "${HOST_PORT}:8000" \
  --restart unless-stopped \
  "$APP_IMAGE"

docker ps --filter "name=$CONTAINER_NAME"
