#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
python3.12 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements-dev.txt
(cd frontend && npm ci --cache ../.cache/npm --no-audit --no-fund)
.venv/bin/python -m scripts.init_db
