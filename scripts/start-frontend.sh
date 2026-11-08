#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/../frontend"
exec npm run dev -- --port 5173 --strictPort
