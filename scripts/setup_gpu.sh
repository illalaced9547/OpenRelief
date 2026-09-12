#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3.12 -m venv .venv-gpu
.venv-gpu/bin/python -m pip install --upgrade pip
.venv-gpu/bin/python -m pip install -r requirements-gpu.txt
.venv-gpu/bin/python -c 'import torch; assert torch.cuda.is_available(), "CUDA required"; print(torch.cuda.get_device_name())'
mkdir -p artifacts
.venv-gpu/bin/python -m pip freeze > artifacts/gpu-environment.lock.txt
