import logging

from django.conf import settings
from django.contrib.gis.geoip2 import GeoIP2, GeoIP2Exception
from django.core.exceptions import MiddlewareNotUsed

logger = logging.getLogger(__name__)


class GeoIP2Middleware(object):

    """
    Add GeoIP country info to each request.

    This middleware will add a `country` attribute to each request
    which contains the Django GeoIP2.country() info, along with the
    IP address against the source IP address used by the lookup.

    The country is stashed in the session, so the actual database
    lookup will only occur once per session, or when the IP address
    changes - so if the user maintains a session but gets on a plane,
    it'll refresh on the other side.

    """
    SESSION_KEY = 'geoip'

    def __init__(self, get_response):
        """Check settings to see if middleware is enabled, and try to init GeoIP2."""
        if not getattr(settings, 'GEOIP2_MIDDLEWARE_ENABLED', False):
            raise MiddlewareNotUsed("GeoIP disabled via settings.GEOIP2_MIDDLEWARE_ENABLED")
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
        geoip = self.get_session_data(request)
        request.session[GeoIP2Middleware.SESSION_KEY] = request.country = geoip
        return self.get_response(request)

    def get_remote_addr(self, request):
        """Return client IP."""
        if 'HTTP_X_FORWARDED_FOR' in request.META:
            # some platforms chain forwarded IP addresses; in Heroku's case
            # the client IP will always be the final one.
            return request.META.get('HTTP_X_FORWARDED_FOR').split(',')[-1]
        else:
            return request.META.get('REMOTE_ADDR')

    def get_country(self, ip_address):
        """Return dict containing country info from GeoIP2."""
        try:
            country = self.geoip2.country(ip_address)
            country['ip_address'] = ip_address
            return country
        except Exception:
            logger.exception("Error raised looking up remote_addr: %s", ip_address)
            return None

    def get_session_data(self, request):
        """Get a dict tuple containing the country info."""
        ip_address = self.get_remote_addr(request)
        data = request.session.get(GeoIP2Middleware.SESSION_KEY)
        if data is None:
            return self.get_country(ip_address)
        if data['ip_address'] != ip_address:
            # stale data, refetch
            return self.get_country(ip_address)
        return data
