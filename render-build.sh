#!/usr/bin/env bash
# Render runs this on every deploy. Each step is idempotent, so a redeploy
# never destroys questions or results.
set -o errexit

pip install --upgrade pip
pip install -r requirements-deploy.txt

python manage.py collectstatic --no-input
python manage.py migrate --no-input

# Only seeds when the database has no quiz at all.
python manage.py seed_quiz --if-empty

# Leaves an existing admin account untouched. If DJANGO_SUPERUSER_PASSWORD
# is unset, a password is generated and printed in this build log -- search
# the log for "Generated admin password".
python manage.py ensure_admin
