#!/usr/bin/env bash
# Start the Task Manager locally. Run from anywhere: ./run.sh
#
# Serves the FastAPI backend on 0.0.0.0:8000 so the LAN can reach it. The API
# reads configuration from the project-root .env (copy .env.example first).
# When the frontend exists, its built assets are served too.
set -euo pipefail

# Always operate from the project root (this script's directory).
cd "$(dirname "$0")"

if [ ! -f .env ]; then
  echo "No .env found. Copy .env.example to .env and set REPO_PATH first." >&2
  exit 1
fi

# Backend virtualenv + dependencies.
if [ ! -d backend/.venv ]; then
  echo "Creating backend virtualenv..."
  python3 -m venv backend/.venv
fi
# shellcheck disable=SC1091
source backend/.venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r backend/requirements.txt

# Optional: build the frontend if present so run.sh serves a full app.
if [ -f frontend/package.json ]; then
  echo "Building frontend..."
  (cd frontend && npm install && npm run build)
fi

# Start the API. --app-dir puts backend/ on the import path while the working
# directory stays at the project root so .env and the SQLite file resolve here.
echo "Starting API on http://0.0.0.0:8000 (docs at /docs)"
exec uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000
