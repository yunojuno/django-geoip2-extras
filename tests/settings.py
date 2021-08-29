from distutils.version import StrictVersion
from os import path

import django

DJANGO_VERSION = StrictVersion(django.get_version())

DEBUG = True
TEMPLATE_DEBUG = True
USE_TZ = True
USE_L10N = True

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": "test.db"}}

INSTALLED_APPS = (
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "geoip2_extras",
)

MIDDLEWARE = [
    # default django middleware
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "geoip2_extras.middleware.GeoIP2Middleware",
]

PROJECT_DIR = path.abspath(path.join(path.dirname(__file__)))

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [path.join(PROJECT_DIR, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.contrib.messages.context_processors.messages",
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.request",
            ]
        },
    }
]

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    },
    "geoip2-extras": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "some-random-string-key",
    },
}

STATIC_URL = "/static/"

SECRET_KEY = "secret"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"simple": {"format": "%(levelname)s %(message)s"}},
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "simple",
        }
    },
    "loggers": {
        "": {"handlers": ["console"], "propagate": True, "level": "DEBUG"},
        "django.request": {
            "handlers": ["console"],
            "propagate": True,
            "level": "DEBUG",
        },
        "geoip2_extras": {
            "handlers": ["console"],
            "propagate": True,
            "level": "DEBUG",
        },
    },
}

ROOT_URLCONF = "tests.urls"

# Uncomment this, and add the GeoIP2-City.mmdb and GeoIP2-Country.mmdb databases
# to the /tests directory.
GEOIP_PATH = PROJECT_DIR
# Test database downloaded from MaxMind's GH repo
# https://github.com/maxmind/MaxMind-DB/tree/main/test-data
GEOIP_COUNTRY = "GeoLite2-Country-Test.mmdb"

if not DEBUG:
    raise Exception("This settings file can only be used with DEBUG=True")
