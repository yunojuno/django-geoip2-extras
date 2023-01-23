from os import path

DEBUG = True

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": "test.db"}}

INSTALLED_APPS = ("geoip2_extras",)

MIDDLEWARE = [
    "django.middleware.common.CommonMiddleware",
    "geoip2_extras.middleware.GeoIP2Middleware",
]

PROJECT_DIR = path.abspath(path.join(path.dirname(__file__)))

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

SECRET_KEY = "geoip2-extras"  # noqa: S105

# Uncomment this, and add the GeoIP2-City.mmdb and GeoIP2-Country.mmdb databases
# to the /tests directory.
GEOIP_PATH = PROJECT_DIR
# Test database downloaded from MaxMind's GH repo
# https://github.com/maxmind/MaxMind-DB/tree/main/test-data
GEOIP_COUNTRY = "GeoLite2-Country-Test.mmdb"

GEOIP2_EXTRAS_CACHE_NAME = "geoip2-extras"

if not DEBUG:
    raise Exception("This settings file can only be used with DEBUG=True")
