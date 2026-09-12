#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PYTHON=${OPEN_RELIEF_PYTHON:-.venv/bin/python}
"$PYTHON" -m open_relief.cli build refrences/hfid_hv1.csv
"$PYTHON" -m open_relief.enrich artifacts/dataset \
  artifacts/monthly-ports.jsonl artifacts/monthly-conflict-prices.jsonl \
  artifacts/monthly-conflict-cod.jsonl artifacts/monthly-rainfall.jsonl \
  artifacts/monthly-extra-conflict-prices.jsonl artifacts/monthly-extra-rainfall.jsonl \
  artifacts/monthly-extra-ports.jsonl --output artifacts/multimodal
"$PYTHON" -m open_relief.validate artifacts/multimodal --output reports/dataset-validation.json
