"""
taxi_project/settings.py
Central settings file – reads from .env via django-environ.
"""
import os
from pathlib import Path
import environ

# ─── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

# ─── Environment ───────────────────────────────────────────────────────────────
env = environ.Env(
    DEBUG=(bool, True),
    ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    USE_LEAFLET=(bool, True),
)
environ.Env.read_env(os.path.join(BASE_DIR, ".env"))

SECRET_KEY = env("SECRET_KEY", default="dev-secret-key-change-in-production")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

# ─── Installed Apps ────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "channels",
    "django_filters",
    # Local
    "taxiapp",
]

# ─── Middleware ─────────────────────────────────────────────────────────────────
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",   # serve static files
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "taxi_project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "taxiapp" / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "taxiapp.context_processors.map_settings",  # injects map keys
            ],
        },
    },
]

# ─── ASGI / Channels ───────────────────────────────────────────────────────────
ASGI_APPLICATION = "taxi_project.asgi.application"

CHANNEL_LAYERS = {
    "default": {
        # Use InMemoryChannelLayer for dev (no Redis needed).
        # For production swap to channels_redis.core.RedisChannelLayer.
        "BACKEND": "channels.layers.InMemoryChannelLayer",
        # "BACKEND": "channels_redis.core.RedisChannelLayer",
        # "CONFIG": {"hosts": [env("REDIS_URL", default="redis://localhost:6379/0")]},
    }
}

# ─── Database ──────────────────────────────────────────────────────────────────
_db_url = env("DATABASE_URL", default="")
if _db_url:
    DATABASES = {"default": env.db("DATABASE_URL")}
else:
    # Default to SQLite for easy local development
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# ─── Auth ──────────────────────────────────────────────────────────────────────
AUTH_USER_MODEL = "taxiapp.User"
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/dashboard/"
LOGOUT_REDIRECT_URL = "/login/"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ─── REST Framework ────────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

# ─── JWT ───────────────────────────────────────────────────────────────────────
from datetime import timedelta
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
}

# ─── CORS ──────────────────────────────────────────────────────────────────────
CORS_ALLOW_ALL_ORIGINS = DEBUG  # In production list specific origins
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",  # React dev server
    "http://127.0.0.1:3000",
]

# ─── Static / Media ────────────────────────────────────────────────────────────
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
STATICFILES_DIRS = [BASE_DIR / "taxiapp" / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ─── Internationalisation ──────────────────────────────────────────────────────
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ─── Maps ──────────────────────────────────────────────────────────────────────
GOOGLE_MAPS_API_KEY = env("GOOGLE_MAPS_API_KEY", default="")
USE_LEAFLET = env("USE_LEAFLET", default=True)  # Free, no key needed

# ─── Stripe ────────────────────────────────────────────────────────────────────
STRIPE_PUBLISHABLE_KEY = env("STRIPE_PUBLISHABLE_KEY", default="")
STRIPE_SECRET_KEY = env("STRIPE_SECRET_KEY", default="")
STRIPE_WEBHOOK_SECRET = env("STRIPE_WEBHOOK_SECRET", default="")

# ─── Fare Settings ─────────────────────────────────────────────────────────────
FARE_BASE = 2.50          # Base fare in USD
FARE_PER_KM = 1.20        # Per kilometre rate
FARE_PER_MIN = 0.25       # Per minute rate
