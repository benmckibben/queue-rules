from pathlib import Path

import sentry_sdk
from decouple import config
from dj_database_url import parse as db_url
from sentry_sdk.integrations.django import DjangoIntegration

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve(strict=True).parent.parent
SECRET_KEY = config("SECRET_KEY")
DEBUG = config("DEBUG", cast=bool)

ALLOWED_HOSTS = [config("HOSTNAME")]

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "social_django",
    "data",
    "frontend",
    "worker",
    "api",
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

ROOT_URLCONF = "queue_rules.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "queue_rules.wsgi.application"


# Database
# https://docs.djangoproject.com/en/3.1/ref/settings/#databases
DATABASES = {
    "default": config(
        "DATABASE_URL",
        default="sqlite:///{}".format(BASE_DIR / "db.sqlite3"),
        cast=db_url,
    ),
}


# Password validation
# https://docs.djangoproject.com/en/3.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",  # noqa: E501
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Internationalization
# https://docs.djangoproject.com/en/3.1/topics/i18n/

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_L10N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.1/howto/static-files/

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "static"


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "WARNING"},
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "queuerd": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}


AUTHENTICATION_BACKENDS = ("social_core.backends.spotify.SpotifyOAuth2",)
LOGIN_REDIRECT_URL = "/"

SOCIAL_AUTH_SPOTIFY_KEY = config("SPOTIFY_CLIENT_ID")
SOCIAL_AUTH_SPOTIFY_SECRET = config("SPOTIFY_SECRET")
SOCIAL_AUTH_SPOTIFY_SCOPE = ["user-modify-playback-state", "user-read-playback-state"]
SPOTIFY_REDIRECT_URI = config("SPOTIFY_REDIRECT_URI")
SOCIAL_AUTH_REDIRECT_IS_HTTPS = config(
    "SOCIAL_AUTH_REDIRECT_IS_HTTPS", default=False, cast=bool
)

SERVICE_STATUS_OK_THRESHOLD = config(
    "SERVICE_STATUS_OK_THRESHOLD", default=15, cast=int
)

# Queuerd config
QUEUERD_SLEEP_TIME = config("QUEUERD_SLEEP_TIME", default=1, cast=float)
QUEUERD_CHECK_INTERVAL = config("QUEUERD_CHECK_INTERVAL", default=5, cast=float)

# Sentry
if not DEBUG:  # pragma: no cover
    sentry_sdk.init(
        dsn=config("SENTRY_DSN"),
        integrations=[DjangoIntegration()],
        send_default_pii=True,
        environment=config("ENVIRONMENT"),
    )
