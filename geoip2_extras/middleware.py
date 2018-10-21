import logging
from typing import Callable

from geoip2.errors import AddressNotFoundError

from django.conf import settings
from django.contrib.gis.geoip2 import GeoIP2, GeoIP2Exception
from django.core.exceptions import MiddlewareNotUsed
from django.core.cache import caches, InvalidCacheBackendError

logger = logging.getLogger(__name__)

GEO_CACHE_TIMEOUT = getattr(settings, 'GEOIP2_EXTRAS_GEO_CACHE_TIMEOUT', 3600)
GEO_DATA_ADDRESS_NOT_FOUND = {
    'country_code': 'XX',
    'country_name': 'unknown'
}


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
            self.cache = caches['geoip2-extras']
            self.geoip2 = GeoIP2()
            # See https://code.djangoproject.com/ticket/28981
            if self.geoip2._reader is None:
                raise GeoIP2Exception("MaxMind database not found at GEOIP_PATH")
        except InvalidCacheBackendError:
            raise MiddlewareNotUsed("GeoIP2 disabled: cache not configured.")
        except GeoIP2Exception:
            raise MiddlewareNotUsed("Error loading GeoIP2 data")
        else:
            self.get_response = get_response

    def __call__(self, request):
        """
        Add country info _before_ view is called.

        The country info is cached against the IP address.

        """
        request.remote_addr = self.remote_addr(request)
        request.geo_data = self.geo_data(request.remote_addr)
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

    def geo_data(self, ip_address: str) -> dict:
        """
        Return GeoIP2data for an IP address.

        If AddressNotFound occurs then we return the unknown
        data, and cache it (as the IP address is not found);
        if the GeoIP2 lookup fails, we return the unknown
        data, but do _not_ cache it, as we want to try again
        on the next request.

        """
        data = self.cache.get(ip_address)
        if data is not None:
            return data
            
        data = self._city_or_country(ip_address)
        if data is None:
            data = GEO_DATA_ADDRESS_NOT_FOUND
            data['remote_addr'] = ip_address
        else:
            data['remote_addr'] = ip_address
            self.cache.set(ip_address, data, GEO_CACHE_TIMEOUT)
        return data

    def _city_or_country(self, ip_address: str) -> dict:
        """Perform the actual GeoIP2 database lookup."""
        try:
            if self.geoip2._city:
                return self.geoip2.city(ip_address)
            else:
                return self.geoip2.country(ip_address)
        except AddressNotFoundError:
            logger.debug("IP address not found in MaxMind database: %s", ip_address)
            return GEO_DATA_ADDRESS_NOT_FOUND
        except GeoIP2Exception:
            logger.exception("GeoIP2 exception raised for %s", ip_address)
        except Exception:
            logger.exception("Error raised looking up geoip2 data for %s", ip_address)
        return {} 
