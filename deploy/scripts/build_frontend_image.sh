#!/usr/bin/env bash
set -euo pipefail

TAG=${TAG:-bidding-frontend:latest}
CONTEXT=${CONTEXT:-frontend}
DOCKERFILE=${DOCKERFILE:-frontend/Dockerfile}

echo "Building frontend image $TAG"
docker build -f "$DOCKERFILE" -t "$TAG" "$CONTEXT"
