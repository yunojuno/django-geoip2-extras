# package settings - read from django.conf.settings with defaults.
from django.conf import settings

# time to cache IP <> address data - default to 1hr
CACHE_TIMEOUT = int(getattr(settings, "GEOIP2_EXTRAS_CACHE_TIMEOUT", 3600))

# set to True to add X-GeoIP2 response headers - defaults to DEBUG value
ADD_RESPONSE_HEADERS = bool(
    getattr(settings, "GEOIP2_EXTRAS_ADD_RESPONSE_HEADERS", settings.DEBUG)
)
