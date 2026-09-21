# Daffodil AI Club quiz — one self-contained image.
# Build:  docker compose build
# Run:    docker compose up

FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencies first, so editing templates or CSS doesn't reinstall Django.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Static files are baked into the image. Their content only changes when the
# image is rebuilt, so there is no reason to redo this on every container start.
# The key here is build-time only and never reaches the running container.
RUN DJANGO_DEBUG=0 \
    DJANGO_SECRET_KEY=build-time-only-not-a-runtime-secret \
    python manage.py collectstatic --noinput --clear

# Run as an ordinary user, not root. /app/data is created here so a named
# volume mounted over it inherits the right ownership.
RUN useradd --create-home --uid 1000 quiz \
    && mkdir -p /app/data \
    && chown -R quiz:quiz /app

USER quiz

ENV DJANGO_DB_PATH=/app/data/db.sqlite3 \
    DJANGO_DEBUG=0 \
    DJANGO_ALLOWED_HOSTS=*

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/', timeout=4).status == 200 else 1)"

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--timeout", "60", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
