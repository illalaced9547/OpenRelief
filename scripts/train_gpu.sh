#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PYTHON=${OPEN_RELIEF_PYTHON:-.venv-gpu/bin/python}
"$PYTHON" -m open_relief.validate artifacts/multimodal \
  --annotations artifacts/annotations-training.jsonl \
  --output reports/pretraining-validation.json
"$PYTHON" -m open_relief.gpu artifacts/multimodal \
  --annotations artifacts/annotations-training.jsonl \
  --output "${1:-artifacts/gpu-run}" --eval-limit 256
