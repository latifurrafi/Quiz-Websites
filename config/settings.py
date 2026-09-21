"""Django settings for the Daffodil AI Club quiz site."""

from pathlib import Path
import os

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

# --- Security -------------------------------------------------------------
# For production set these via environment variables (see .env.example).
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-dev-only-key-change-me-before-deploying-0a9f83kd",
)
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]").split(",")
    if h.strip()
]
CSRF_TRUSTED_ORIGINS = [
    o.strip()
    for o in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if o.strip()
]

# Render gives each service its public hostname at runtime, so the deploy does
# not have to hard-code a URL that is only known after the first deploy.
RENDER_HOST = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "").strip()
if RENDER_HOST:
    if RENDER_HOST not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(RENDER_HOST)
    origin = f"https://{RENDER_HOST}"
    if origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(origin)

# --- Applications ---------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "quiz",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# --- Database -------------------------------------------------------------
# Hosting platforms hand the app a DATABASE_URL. When one is present it wins.
# Otherwise we stay on SQLite, which is what local and Docker runs use.
# DJANGO_DB_PATH lets Docker put the SQLite file on a mounted volume, so the
# questions and results survive rebuilding the image.
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()

# Render's filesystem is wiped on every restart, so a SQLite file there would
# silently lose every result. Refuse to start rather than lose people's scores.
if os.environ.get("RENDER") and not DATABASE_URL:
    raise ImproperlyConfigured(
        "Running on Render without DATABASE_URL. Render's disk is ephemeral, so "
        "a SQLite database would be erased on every restart and deploy. Attach a "
        "Postgres database (Neon's free tier works) and set DATABASE_URL."
    )

if DATABASE_URL:
    try:
        import dj_database_url
    except ModuleNotFoundError as exc:  # pragma: no cover - deploy-only path
        raise ImproperlyConfigured(
            "DATABASE_URL is set but dj-database-url is not installed. "
            "Install from requirements-deploy.txt."
        ) from exc

    DATABASES = {
        "default": dj_database_url.parse(DATABASE_URL, conn_max_age=600),
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": os.environ.get("DJANGO_DB_PATH", BASE_DIR / "db.sqlite3"),
            "OPTIONS": {"timeout": 20},
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- I18N -----------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Dhaka"
USE_I18N = True
USE_TZ = True

# --- Static & media -------------------------------------------------------
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
        if not DEBUG
        else "django.contrib.staticfiles.storage.StaticFilesStorage"
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Session --------------------------------------------------------------
# Participants are tracked by an attempt token in their session, not by login.
SESSION_COOKIE_AGE = 60 * 60 * 6  # 6 hours is plenty for an event
SESSION_SAVE_EVERY_REQUEST = True

# --- HTTPS hardening ------------------------------------------------------
# Off by default so an HTTP-only deploy still works. Set DJANGO_SECURE_HTTPS=1
# once the site is actually served over TLS -- secure cookies break sessions
# entirely if the site is still on plain HTTP.
SECURE_HTTPS = os.environ.get("DJANGO_SECURE_HTTPS", "0") == "1"

if SECURE_HTTPS:
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    # Read the HSTS docs before raising this -- it is hard to undo.
    SECURE_HSTS_SECONDS = int(os.environ.get("DJANGO_HSTS_SECONDS", 3600))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    SECURE_HSTS_PRELOAD = False

SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# --- Branding shown in templates -----------------------------------------
SITE_NAME = "Daffodil AI Club"
SITE_TAGLINE = "Department of CSE"
