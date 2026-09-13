#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

: "${NEBIUS_REGION:?Set NEBIUS_REGION, e.g. eu-north1}"
: "${NEBIUS_BUCKET:?Set NEBIUS_BUCKET to your Object Storage bucket name}"

ENDPOINT="https://storage.${NEBIUS_REGION}.nebius.cloud"

aws --endpoint-url "$ENDPOINT" s3 sync artifacts/multimodal "s3://${NEBIUS_BUCKET}/multimodal" \
  --exclude ".*"

echo "Uploaded artifacts/multimodal to s3://${NEBIUS_BUCKET}/multimodal"
echo "Mount it in the job with: --volume s3://${NEBIUS_BUCKET}:/workspace/data:ro"
