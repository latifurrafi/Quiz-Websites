#!/usr/bin/env bash
# Start the AI Club quiz without Docker.
#
#   ./run.sh
#
# Creates a virtual environment, installs dependencies, prepares the database
# and starts the server. Safe to run repeatedly -- nothing is destroyed.

set -euo pipefail
cd "$(dirname "$0")"

PORT="${PORT:-8000}"
VENV=".venv"

# --- find a usable Python ---------------------------------------------------
PY=""
for candidate in python3.13 python3.12 python3 python; do
  if command -v "$candidate" >/dev/null 2>&1; then
    if "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3,12) else 1)' 2>/dev/null; then
      PY="$candidate"
      break
    fi
  fi
done

if [ -z "$PY" ]; then
  echo "ERROR: Python 3.12 or newer is required but was not found."
  echo
  echo "  macOS:    brew install python@3.13"
  echo "  Ubuntu:   sudo apt install python3 python3-venv"
  echo "  Windows:  https://www.python.org/downloads/  (tick 'Add to PATH')"
  exit 1
fi
echo "==> Using $($PY --version)"

# --- environment ------------------------------------------------------------
if [ ! -d "$VENV" ]; then
  echo "==> Creating the virtual environment (first run only)"
  "$PY" -m venv "$VENV"
fi

PIP="$VENV/bin/pip"
PYBIN="$VENV/bin/python"

echo "==> Installing dependencies"
"$PIP" install --quiet --upgrade pip
"$PIP" install --quiet -r requirements.txt

# --- database ---------------------------------------------------------------
echo "==> Preparing the database"
"$PYBIN" manage.py migrate --noinput

echo "==> Checking for a quiz"
"$PYBIN" manage.py seed_quiz --if-empty

echo "==> Checking for an admin account"
"$PYBIN" manage.py ensure_admin

# --- go ---------------------------------------------------------------------
cat <<BANNER

  ---------------------------------------------------------
   Quiz          http://127.0.0.1:$PORT
   Admin panel   http://127.0.0.1:$PORT/admin/

   Others on this Wi-Fi can join at your machine's address
   on port $PORT. Press Ctrl+C to stop.
  ---------------------------------------------------------

BANNER

exec "$PYBIN" manage.py runserver "0.0.0.0:$PORT"
