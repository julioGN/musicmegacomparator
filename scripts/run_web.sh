#!/usr/bin/env bash
set -euo pipefail

# Kill anything already running on 8501 (Streamlit default)
if lsof -ti:8501 >/dev/null 2>&1; then
  echo "Killing process on port 8501..."
  lsof -ti:8501 | xargs kill -9 || true
fi

# Run Streamlit web app
echo "Starting Streamlit on http://localhost:8501 ..."
PYTHONPATH=musicweb/src streamlit run musicweb/src/musicweb/web/app.py --server.port 8501 "$@"

