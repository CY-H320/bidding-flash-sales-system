#!/usr/bin/env bash
set -euo pipefail

AWS_ACCOUNT_ID=${AWS_ACCOUNT_ID:?Set AWS_ACCOUNT_ID}
AWS_REGION=${AWS_REGION:-ap-northeast-1}
TAG=${TAG:-latest}
BACKEND_IMAGE=${BACKEND_IMAGE:-bidding-api:latest}
FRONTEND_IMAGE=${FRONTEND_IMAGE:-bidding-frontend:latest}
BACKEND_REPO=${BACKEND_REPO:-bidding-api}
FRONTEND_REPO=${FRONTEND_REPO:-bidding-frontend}

ECR_BASE="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

echo "Logging in to ECR ${ECR_BASE}"
aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$ECR_BASE"

echo "Tagging images"
docker tag "$BACKEND_IMAGE" "$ECR_BASE/${BACKEND_REPO}:$TAG"
docker tag "$FRONTEND_IMAGE" "$ECR_BASE/${FRONTEND_REPO}:$TAG"

echo "Pushing images"
docker push "$ECR_BASE/${BACKEND_REPO}:$TAG"
docker push "$ECR_BASE/${FRONTEND_REPO}:$TAG"
