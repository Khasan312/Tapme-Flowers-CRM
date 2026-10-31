import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR.parent / ".env")
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
DEBUG = os.getenv("DJANGO_DEBUG", "false").lower() == "true"
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "tapme.accounts",
    "tapme.businesses",
    "tapme.customers",
    "tapme.catalog",
    "tapme.orders",
    "tapme.payments",
    "tapme.media",
    "tapme.feedback",
    "tapme.reminders",
    "tapme.messaging",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
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
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]
WSGI_APPLICATION = "config.wsgi.application"
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "tapme_flowers"),
        "USER": os.getenv("POSTGRES_USER", "tapme"),
        "PASSWORD": os.environ["POSTGRES_PASSWORD"],
        "HOST": os.getenv("POSTGRES_HOST", "127.0.0.1"),
        "PORT": os.getenv("POSTGRES_PORT", "55432"),
        "CONN_MAX_AGE": 0,
        "OPTIONS": {"connect_timeout": 5},
    }
}
AUTH_USER_MODEL = "accounts.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LANGUAGE_CODE = "ru"
TIME_ZONE = "Asia/Bishkek"
USE_I18N = True
USE_TZ = True
STATIC_URL = "/static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
CSRF_FAILURE_VIEW = "config.errors.csrf_failure"
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "config.errors.exception_handler",
    "DEFAULT_THROTTLE_RATES": {"login": "10/minute", "public": "60/minute"},
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
}
SPECTACULAR_SETTINGS = {
    "TITLE": "Tapme Flowers API",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "ENUM_NAME_OVERRIDES": {
        "PaymentKind": ["payment", "refund"],
        "FeedbackKind": ["review", "complaint"],
        "PhotoKind": ["bouquet", "delivery"],
        "ExportKind": ["csv", "xlsx"],
    },
}

MEDIA_ROOT = Path(os.getenv("TAPME_MEDIA_ROOT", str(BASE_DIR.parent / "media")))
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    "photos": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {"location": MEDIA_ROOT},
    },
}
if os.getenv("TAPME_PHOTO_STORAGE") == "s3":
    STORAGES["photos"] = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": os.environ["AWS_STORAGE_BUCKET_NAME"],
            "endpoint_url": os.getenv("AWS_S3_ENDPOINT_URL"),
            "region_name": os.getenv("AWS_S3_REGION_NAME"),
            "default_acl": None,
            "file_overwrite": False,
            "querystring_auth": True,
        },
    }
DATA_UPLOAD_MAX_MEMORY_SIZE = 12 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_BEAT_SCHEDULE = {
    "refresh-reminders": {"task": "tapme.reminders.tasks.generate_reminders", "schedule": 900.0},
    "process-messages": {"task": "tapme.messaging.tasks.process_messages", "schedule": 10.0},
    "maintain-order-drafts": {"task": "tapme.orders.tasks.maintain_order_drafts", "schedule": 60.0},
}

META_APP_SECRET = os.getenv("META_APP_SECRET", "")
META_WEBHOOK_VERIFY_TOKEN = os.getenv("META_WEBHOOK_VERIFY_TOKEN", "")
META_GRAPH_VERSION = os.getenv("META_GRAPH_VERSION", "")
TAPME_SECRETS_KEY = os.getenv("TAPME_SECRETS_KEY", "")
TAPME_META_MODE = os.getenv("TAPME_META_MODE", "live")

# Off by default. Demo never sends data outside the local process.
TAPME_AI_ENABLED = os.getenv("TAPME_AI_ENABLED", "false").lower() == "true"
TAPME_AI_MODE = os.getenv("TAPME_AI_MODE", "mistral")
TAPME_AI_MODEL = os.getenv("TAPME_AI_MODEL", "ministral-3b-2512")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
# Optional local trial: only this fake conversation may reach the external model.
TAPME_AI_TEST_CHAT_ID = os.getenv("TAPME_AI_TEST_CHAT_ID", "").strip()
CELERY_BEAT_SCHEDULE["extract-order-drafts"] = {
    "task": "tapme.orders.tasks.extract_order_drafts",
    "schedule": 5.0,
}

STATIC_ROOT = (
    Path("/data/static") if os.getenv("TAPME_MEDIA_ROOT") else BASE_DIR.parent / "staticfiles"
)
CSRF_TRUSTED_ORIGINS = [
    origin for origin in os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if origin
]
if os.getenv("DJANGO_TRUST_PROXY") == "true":
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = not DEBUG
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_AGE = 60 * 60 * 12
if os.getenv("CACHE_URL"):
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": os.environ["CACHE_URL"],
        }
    }
