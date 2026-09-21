#!/bin/sh
# Prepare the database, then hand over to whatever the CMD is.
# Every step here is idempotent -- restarting never destroys existing data.
set -e

echo "==> Applying database migrations"
python manage.py migrate --noinput

echo "==> Checking for a quiz"
python manage.py seed_quiz --if-empty

echo "==> Checking for an admin account"
python manage.py ensure_admin

echo "==> Starting the quiz site on port 8000"
exec "$@"
