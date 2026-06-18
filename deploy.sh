#!/bin/bash
set -euo pipefail

DEPLOY_HOST="${DEPLOY_HOST:-Baidu-server-2c4g-bot-server-manager}"
DEPLOY_PATH="${DEPLOY_PATH:-/opt/gpu-cluster-monitor}"

echo "==> Deploying to ${DEPLOY_HOST}:${DEPLOY_PATH}..."

ssh "$DEPLOY_HOST" "mkdir -p $DEPLOY_PATH"

rsync -avz --delete \
  --exclude '.git' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude '.env' \
  --exclude '.venv' \
  --exclude '*.egg-info' \
  --exclude 'Auwomo-H200*' \
  --exclude 'volcano-pytorch*' \
  --exclude 'openclaw.json' \
  ./ "${DEPLOY_HOST}:${DEPLOY_PATH}/"

echo "==> Installing Python CLI..."
ssh "$DEPLOY_HOST" "cd ${DEPLOY_PATH}/cli && pip install -e . 2>&1 | tail -3"

echo "==> Done! CLI installed on ${DEPLOY_HOST}."
echo "    Test: ssh ${DEPLOY_HOST} 'gpu-metrics health'"
