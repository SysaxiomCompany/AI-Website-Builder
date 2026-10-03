#!/usr/bin/env bash
# Retrain and evaluate the two classifiers (macOS / Linux): venv + install + train + evaluate.
# Needs the team's ML-Training-App folder (default ../ML-Training-App, or set ML_TRAINING_APP).
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
python ml/train.py
python ml/evaluate.py
echo "Done. New files are in ml/artifacts/ and the plot is docs/test-evidence/ml-evaluation.png"
