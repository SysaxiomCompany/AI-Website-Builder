#!/usr/bin/env bash
# AI Website Builder - macOS / Linux: create the venv if missing, install, run on http://127.0.0.1:5050
set -e
cd "$(dirname "$0")"
PY="${PYTHON:-python3}"
if ! "$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'; then
  echo "Python 3.11 or newer is needed (the pinned packages require it). Set PYTHON=/path/to/python3.11 and retry." >&2
  exit 1
fi
if [ ! -d .venv ]; then "$PY" -m venv .venv; fi
# shellcheck disable=SC1091
. .venv/bin/activate
if ! cmp -s requirements.txt .venv/.requirements.stamp 2>/dev/null; then
  python -m pip install -r requirements.txt
  cp requirements.txt .venv/.requirements.stamp
fi
[ -f .env ] || cp .env.example .env
exec python app.py
