#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PYTHON=${OPEN_RELIEF_PYTHON:-.venv/bin/python}
case "${1:-pilot}" in
  pilot) "$PYTHON" -m open_relief.annotation artifacts/multimodal --limit 6 --workers 3 \
           --budget-usd 2 --output artifacts/annotations-final-pilot.jsonl ;;
  full) "$PYTHON" -m open_relief.annotation artifacts/multimodal --all --workers 8 \
          --budget-usd 185 --output artifacts/annotations-training.jsonl ;;
  *) echo 'Usage: bash scripts/annotate_local.sh [pilot|full]' >&2; exit 2 ;;
esac
