#!/usr/bin/env bash
set -euo pipefail

TAG=${TAG:-bidding-api:latest}
CONTEXT=${CONTEXT:-backend}
DOCKERFILE=${DOCKERFILE:-backend/Dockerfile}

echo "Building backend image $TAG"
docker build -f "$DOCKERFILE" -t "$TAG" "$CONTEXT"
