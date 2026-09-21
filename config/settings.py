"""Django settings for the Daffodil AI Club quiz site.

Runs locally on SQLite with debug on. On Render, DEBUG switches itself off and
WhiteNoise serves the static files.
"""

from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-dev-only-key-0a9f83kd-change-if-this-ever-goes-public",
)
# Render sets RENDER=true on every service. Default DEBUG off there, so a
# stray error page can never leak settings and file paths to visitors.
ON_RENDER = bool(os.environ.get("RENDER"))
DEBUG = os.environ.get("DJANGO_DEBUG", "0" if ON_RENDER else "1") == "1"

# A list comprehension cannot also contain loose literal items -- the extra
# host goes in the default string instead, where it is just another entry.
ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get(
        "DJANGO_ALLOWED_HOSTS",
        "localhost,127.0.0.1,[::1],quiz-websites-9lj9.onrender.com",
    ).split(",")
    if h.strip()
]

# Render hands each service its own public hostname at runtime, so renaming
# the service or adding a custom domain does not need a code change.
RENDER_HOST = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "").strip()
if RENDER_HOST and RENDER_HOST not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RENDER_HOST)

# Django 4+ checks the Origin header on every POST. Without this, logging into
# the admin and submitting the quiz both fail with a CSRF error over HTTPS.
LOCAL_HOSTS = {"localhost", "127.0.0.1", "[::1]"}
CSRF_TRUSTED_ORIGINS = [f"https://{h}" for h in ALLOWED_HOSTS if h not in LOCAL_HOSTS]

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
    # Gunicorn does not serve static files. Without this the deployed site
    # loads with no CSS or JavaScript at all.
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

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Dhaka"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# With the manifest storage, a template referencing a file that was not
# collected raises a 500. Non-strict mode serves it unhashed instead, so a
# forgotten collectstatic degrades to a stale cache rather than a dead site.
WHITENOISE_MANIFEST_STRICT = False

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        )
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Participants are tracked by an attempt token in their session, not by login.
SESSION_COOKIE_AGE = 60 * 60 * 6
SESSION_SAVE_EVERY_REQUEST = True

# Render terminates TLS, so cookies can safely be marked secure there.
if ON_RENDER:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# Branding shown in templates
SITE_NAME = "Daffodil AI Club"
SITE_TAGLINE = "Department of CSE"
