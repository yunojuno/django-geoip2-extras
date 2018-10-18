import logging
from typing import Callable

from geoip2.errors import AddressNotFoundError

from django.conf import settings
from django.contrib.gis.geoip2 import GeoIP2, GeoIP2Exception
from django.core.exceptions import MiddlewareNotUsed
from django.core.cache import caches, InvalidCacheBackendError

logger = logging.getLogger(__name__)
try:
    GEO_CACHE = caches['geoip2']
except InvalidCacheBackendError:
    logger.warning("GeoIP2 disabled as no 'geoip2' cache is configured")
    GEO_CACHE = None

GEO_CACHE_TIMEOUT = getattr(settings, 'GEOIP2_EXTRAS_GEO_CACHE_TIMEOUT', 3600)


class GeoData(object):

    """Container for GeoIP2 return data."""

    UNKNOWN_COUNTRY_CODE = 'XX'
    UNKNOWN_COUNTRY_NAME = 'unknown'

    def __init__(self, ip_address, **geoip_data):
        self.ip_address = ip_address
        self.city = geoip_data.get('city')
        self.country_code = geoip_data.get('country_code')
        self.country_name = geoip_data.get('country_name')
        self.dma_code = geoip_data.get('dma_code')
        self.latitude = geoip_data.get('latitude')
        self.longitude = geoip_data.get('longitude')
        self.postal_code = geoip_data.get('postal_code')
        self.region = geoip_data.get('region')

    @property
    def is_unknown(self):
        return self.country_code == GeoData.UNKNOWN_COUNTRY_CODE

    @classmethod
    def unknown_country(cls, ip_address):
        """Return a new GeoData object representing an unknown country."""
        return GeoData(
            ip_address=ip_address,
            country_code=GeoData.UNKNOWN_COUNTRY_CODE,
            country_name=GeoData.UNKNOWN_COUNTRY_NAME
        )


class GeoIP2Middleware(object):

    """
    Add GeoIP country info to each request.

    This middleware will add a `country` attribute to each request
    which contains the Django GeoIP2.country() info, along with the
    source IP address used by the lookup.

    The country is stashed in the session, so the actual database
    lookup will only occur once per session, or when the IP address
    changes.

    """

    def __init__(self, get_response):
        """Check settings to see if middleware is enabled, and try to init GeoIP2."""
        try:
            self.geoip2 = GeoIP2()
            # See https://code.djangoproject.com/ticket/28981
            if self.geoip2._reader is None:
                raise GeoIP2Exception("MaxMind database not found at GEOIP_PATH")
        except GeoIP2Exception:
            raise MiddlewareNotUsed("Error loading GeoIP2 data")
        else:
            self.get_response = get_response

    def __call__(self, request):
        """
        Add country info _before_ view is called.

        The country info is cached against the IP address.

        """
        ip_address = self.remote_addr(request)
        request.geo_data = self.geo_data(ip_address)
        return self.get_response(request)

    def remote_addr(self, request):
        """Return client IP."""
        header = (
            request.META.get('HTTP_X_FORWARDED_FOR') or
            request.META.get('REMOTE_ADDR') or
            '0.0.0.0'
        )
        # The last IP in the chain is the only one that Heroku can guarantee
        # - prior IPs may be spoofed, but this is the one that connected to
        # the Heroku routing infrastructure. NB if the request came through
        # a proxy this may be the proxy IP. The first IP in the list _should_
        # be the original client, but Heroku can't guarantee that as HTTP
        # headers can be spoofed. Basically - don't bet the farm on an IP
        # being correct, but we know the last one is the one that connected
        # to Heroku.
        # http://stackoverflow.com/a/37061471/45698
        return header.split(',')[-1]

    def geo_data(self, ip_address: str) -> GeoData:
        """
        Return GeoIP2data for an IP address.

        If we have a GEO_CACHE set, then lookup in that first, else we do
        the GeoIP2 lookup on each request.

        """
        if GEO_CACHE is None:
            data = self._geo_data_lookup(ip_address)
        else:
            data = GEO_CACHE(ip_address) or self._geo_data_lookup(ip_address)
            GEO_CACHE.set(ip_address, data, GEO_CACHE_TIMEOUT)
        return data

    @property
    def _geo_data_func(self) -> Callable[[str], dict]:
        """Return the GeoIP2 lookup function to use, based on available database."""
        geo = self.geoip2
        return geo.city if geo._city else geo.country

    def _geo_data_lookup(self, ip_address: str) -> GeoData:
        """Perform the actual GeoIP2 database lookup."""
        try:
            data = self._geo_data_func(ip_address)
        except AddressNotFoundError:
            logger.debug("IP address not found in MaxMind database: %s", ip_address)
            return GeoData.unknown_country(ip_address)
        except GeoIP2Exception:
            logger.exception("GeoIP2 exception raised for %s", ip_address)
        except Exception:
            logger.exception("Error raised looking up geoip2 data for %s", ip_address)
        else:
            return GeoData(ip_address, **data)
