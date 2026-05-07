from datetime import timedelta
from pathlib import Path

import dj_database_url
from decouple import config

# settings/base.py -> settings/ -> config/ -> app/ -> src/ -> <project root>
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent

SECRET_KEY = config("SECRET_KEY")
DEBUG = config("DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS", default="", cast=lambda v: [s.strip() for s in v.split(",") if s.strip()]
)

DJANGO_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "channels",
    "django_celery_results",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    "corsheaders",
]

LOCAL_APPS = [
    "app.core",
    "app.users",
    "app.chat",
    "app.ai",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    # First so every other middleware/view runs inside the request-id
    # logger context and shows up under the same id in logs.
    "app.core.middleware.RequestIdMiddleware",
    # Second: needs request_id already bound, AuthenticationMiddleware not
    # yet applied (we read request.user *after* get_response returns, by
    # which point auth has run). One structured access log per request.
    "app.core.middleware.HttpAccessLogMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "app.config.urls"
WSGI_APPLICATION = "app.config.wsgi.application"
ASGI_APPLICATION = "app.config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

DATABASES = {
    "default": dj_database_url.parse(
        config("DATABASE_URL"),
        conn_max_age=60,
    ),
}

AUTH_USER_MODEL = "users.User"

# ==============================================================================
# Authentication
# ==============================================================================

# It's an educational project so our passwords will simple for demo signups.
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 4},
    },
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ==============================================================================
# Logging
# ==============================================================================
# loguru is wired up in app.config.logging (called from manage.py / wsgi.py /
# asgi.py / celery.py). Django ships a DEFAULT_LOGGING dict that attaches a
# StreamHandler to the "django" logger — child loggers like
# "django.channels.server" propagate up to it AND to root, which is how the
# same access-log line ended up printed twice (once raw via Django's stream,
# once formatted via our InterceptHandler at root). Overriding the "django"
# logger here with handlers=[] and propagate=True keeps the records flowing
# to root (and from there into loguru) but drops the duplicate stream.
_LOGGING_NEUTRAL = (
    "django",
    "django.server",
    "daphne",
    "daphne.server",
    "daphne.http_protocol",
    "daphne.ws_protocol",
    "channels",
    "channels.server",
)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "loggers": {
        # Neutralised so they propagate to root (where loguru picks them up)
        # without their own StreamHandler double-printing.
        **{name: {"handlers": [], "propagate": True, "level": "INFO"} for name in _LOGGING_NEUTRAL},
        # Silenced at ERROR: HttpAccessLogMiddleware already writes a richer
        # line per request (method/path/status/duration/user/view), and
        # these loggers were just duplicating it.
        # - daphne's "HTTP GET /foo 200 [...]" access log
        # - django.request's "Unauthorized: /foo" / "Bad Request: /foo"
        # ERROR still surfaces real 5xx server errors from either logger.
        "django.channels.server": {"handlers": [], "propagate": True, "level": "ERROR"},
        "django.request": {"handlers": [], "propagate": True, "level": "ERROR"},
        "daphne.management.commands.runserver": {
            "handlers": [],
            "propagate": True,
            "level": "ERROR",
        },
    },
}

# ==============================================================================
# Celery
# ==============================================================================

CELERY_BROKER_URL = config("CELERY_BROKER_URL", default="redis://redis:6379/0")
CELERY_RESULT_BACKEND = "django-db"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"

# ==============================================================================
# Email
# ==============================================================================

EMAIL_BACKEND = config("EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = config("EMAIL_HOST", default="mailhog")
EMAIL_PORT = config("EMAIL_PORT", default=1025, cast=int)
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=False, cast=bool)
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="noreply@llm-portrait.local")

# ==============================================================================
# Cache (Redis) — shared state for rate-limit across gunicorn workers
# ==============================================================================

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": config("REDIS_CACHE_URL", default="redis://redis:6379/1"),
    }
}

# ==============================================================================
# Channels (ASGI / WebSocket layer)
# ==============================================================================

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [config("REDIS_CHANNELS_URL", default="redis://redis:6379/2")],
        },
    },
}

# ==============================================================================
# LLM
# ==============================================================================

OLLAMA_URL = config("OLLAMA_URL", default="http://ollama:11434")
OLLAMA_MODEL = config("OLLAMA_MODEL", default="llama3.2:3b")
LLM_RATE_LIMIT = config("LLM_RATE_LIMIT", default="2/m")

# ==============================================================================
# DRF
# ==============================================================================

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "LLM Portrait API",
    "DESCRIPTION": (
        "REST API for the LLM Portrait project.\n\n"
        "The real-time WebSocket chat side is documented separately as an "
        "[AsyncAPI specification](/ws/docs/) — same project, different "
        "transport."
    ),
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# ==============================================================================
# CORS
# ==============================================================================

CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="",
    cast=lambda v: [s.strip() for s in v.split(",") if s.strip()],
)
