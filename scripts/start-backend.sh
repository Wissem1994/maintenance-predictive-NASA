#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
.venv/bin/python -m scripts.init_db
exec .venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
