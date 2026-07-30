# -*- coding: utf-8 -*-
"""Django settings for JobPilot web dashboard."""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent          # .../JobPilot/web
JOBPILOT_ROOT = BASE_DIR.parent                            # .../JobPilot
sys.path.insert(0, str(JOBPILOT_ROOT))                    # so we can import core.*

# Load JobPilot's .env (same secrets the agents use)
try:
    from dotenv import load_dotenv
    load_dotenv(JOBPILOT_ROOT / ".env")
except ImportError:
    pass

import os
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-only-key-change-in-production-xyz123")
# DEBUG is True locally, False in the cloud (set DJANGO_DEBUG=false on Render)
DEBUG = os.getenv("DJANGO_DEBUG", "true").lower() != "false"
ALLOWED_HOSTS = ["*"]                                      # single-user app; Render domain varies
CSRF_TRUSTED_ORIGINS = ["https://*.onrender.com"]

INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "dashboard",
]

MIDDLEWARE = [
    "whitenoise.middleware.WhiteNoiseMiddleware",           # serves static files in the cloud
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
]

ROOT_URLCONF = "jobpilot_web.urls"

TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": ["django.template.context_processors.csrf"]},
}]

WSGI_APPLICATION = "jobpilot_web.wsgi.application"

# Django needs a DB for its own machinery; our real data is in Supabase.
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3",
                         "NAME": BASE_DIR / "django_internal.sqlite3"}}

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
