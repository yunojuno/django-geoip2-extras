import logging

from geoip2.errors import AddressNotFoundError

from django.contrib.gis.geoip2 import GeoIP2, GeoIP2Exception
from django.core.exceptions import MiddlewareNotUsed

logger = logging.getLogger(__name__)


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
    SESSION_KEY = 'geoip2'
    UNKNOWN_COUNTRY_CODE = 'XX'
    UNKNOWN_COUNTRY_NAME = 'unknown'

    def __init__(self, get_response):
        """Check settings to see if middleware is enabled, and try to init GeoIP2."""
        try:
            self.geoip2 = GeoIP2()
        except GeoIP2Exception:
            raise MiddlewareNotUsed("Error loading GeoIP2 data")
        self.get_response = get_response

    def __call__(self, request):
        """
        Add country info _before_ view is called.

        The country info is stored in the session between requests,
        so we don't have to do the lookup on each request, unless the
        client IP has changed.

        """
        ip_address = self.remote_addr(request)
        data = request.session.get(GeoIP2Middleware.SESSION_KEY)
        if data is None:
            data = self.country(ip_address)
        elif data['ip_address'] != ip_address:
            data = self.country(ip_address)
        request.session[GeoIP2Middleware.SESSION_KEY] = request.country = data
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

    def country(self, ip_address):
        """
        Return dict containing country info from GeoIP2.

        This method does the actual lookup. If the address cannot be found (
        e.g. localhost) then it will still return a dict that can be stashed
        in the session to prevent repeated invalid lookups. If the lookup raises
        any other exception it returns None, so that future requests _will_
        repeat the lookup.

        """
        try:
            country = self.geoip2.country(ip_address)
            country['ip_address'] = ip_address
            return country
        except AddressNotFoundError:
            logger.debug("IP address not found in MaxMind database: %s", ip_address)
            return {
                'ip_address': ip_address,
                'country_code': GeoIP2Middleware.UNKNOWN_COUNTRY_CODE,
                'country_name': GeoIP2Middleware.UNKNOWN_COUNTRY_NAME
            }
        except Exception:
            logger.exception("Error raised looking up remote_addr: %s", ip_address)
            return None
