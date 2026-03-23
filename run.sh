#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# Mind Dump — startup script for Debian 12
# Sets production environment, loads .env, initialises DB, starts Flask.
# ──────────────────────────────────────────────────────────────────────────────
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Enforce production mode — never run with debug=True
export FLASK_ENV=production
export FLASK_DEBUG=0

# Load environment variables from .env
if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
else
  echo "ERROR: .env file not found."
  echo "Copy .env.example to .env and set SECRET_KEY before starting."
  exit 1
fi

# Verify required env vars
if [ -z "$SECRET_KEY" ] || [ "$SECRET_KEY" = "replace-this-with-a-long-random-string" ]; then
  echo "ERROR: SECRET_KEY is not set or is still the placeholder value."
  echo "Edit .env and set a strong random SECRET_KEY."
  exit 1
fi

# Check vendor assets are present
if [ ! -f static/vendor/bootstrap.min.css ]; then
  echo "Vendor assets not found. Running setup_assets.sh first…"
  bash setup_assets.sh
fi

# Activate virtualenv if present
if [ -d venv/bin ]; then
  # shellcheck disable=SC1091
  source venv/bin/activate
fi

# Initialise database and create first user if needed, then start server
exec python app.py
