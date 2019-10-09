import logging

from django.conf import settings
from django.contrib.gis.geoip2 import GeoIP2, GeoIP2Exception
from django.core.exceptions import MiddlewareNotUsed
from geoip2.errors import AddressNotFoundError

logger = logging.getLogger(__name__)


class GeoData(object):
    """Container for GeoIP2 return data."""

    UNKNOWN_COUNTRY_CODE = "XX"
    UNKNOWN_COUNTRY_NAME = "unknown"

    def __init__(self, ip_address, **geoip_data):
        self.ip_address = ip_address
        self.city = geoip_data.get("city", "")
        self.country_code = geoip_data.get("country_code", "")
        self.country_name = geoip_data.get("country_name", "")
        self.dma_code = geoip_data.get("dma_code", "")
        self.latitude = geoip_data.get("latitude", "")
        self.longitude = geoip_data.get("longitude", "")
        self.postal_code = geoip_data.get("postal_code", "")
        self.region = geoip_data.get("region", "")

    def __str__(self):
        return f"GeoIP2 data for {self.ip_address}"

    def __repr__(self):
        return f'<GeoIP2 ip_address="{self.ip_address}">'

    @property
    def is_unknown(self):
        return self.country_code == GeoData.UNKNOWN_COUNTRY_CODE

    @classmethod
    def unknown_country(cls, ip_address):
        """Return a new GeoData object representing an unknown country."""
        return GeoData(
            ip_address=ip_address,
            country_code=GeoData.UNKNOWN_COUNTRY_CODE,
            country_name=GeoData.UNKNOWN_COUNTRY_NAME,
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

    SESSION_KEY = "geoip2"

    def __init__(self, get_response):
        """Check settings to see if middleware is enabled, and try to init GeoIP2."""
        try:
            self.geoip2 = GeoIP2()
        except GeoIP2Exception:
            raise MiddlewareNotUsed("Error loading GeoIP2 data")
        if self.geoip2._city:
            logger.debug("Found GeoIP2 City database")
        if self.geoip2._country:
            logger.debug("Found GeoIP2 Country database")
        self.get_response = get_response

    def __call__(self, request):
        """
        Add country info _before_ view is called.

        The country info is stored in the session between requests,
        so we don't have to do the lookup on each request, unless the
        client IP has changed.

        """
        try:
            ip_address = self.remote_addr(request)
            _data = request.session.get(GeoIP2Middleware.SESSION_KEY)
            if _data is None:
                data = self.get_geo_data(ip_address)
            else:
                # deserialize from dict stored in session (object not JSON serializable)
                data = GeoData(**_data)

            if data.ip_address != ip_address:
                data = self.get_geo_data(ip_address)
        except:
            logger.exception("Error fetching GeoData")
            return self.get_response(request)
        else:
            request.geo_data = data
            request.session[GeoIP2Middleware.SESSION_KEY] = data.__dict__
            response = self.get_response(request)
            response["X-GeoIP-Country-Code"] = data.country_code
            return response

    def remote_addr(self, request):
        """Return client IP."""
        header = (
            request.META.get("HTTP_X_FORWARDED_FOR")
            or request.META.get("REMOTE_ADDR")
            or "0.0.0.0"
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
        return header.split(",")[-1].strip()

    def get_geo_data(self, ip_address):
        """Return City and / or Country data for an IP address."""
        return self.city(ip_address) if self.geoip2._city else self.country(ip_address)

    def country(self, ip_address):
        """Return GeoIP2 Country database data."""
        return self._geoip2(ip_address, self.geoip2.country)

    def city(self, ip_address):
        """Return GeoIP2 City database data."""
        return self._geoip2(ip_address, self.geoip2.city)

    def _geoip2(self, ip_address, geo_func):
        """
        Return GeoData object containing info from GeoIP2.

        This method does the actual lookup, using the geoip2 method specified.

        Args:
            ip_address:  the IP address to look up, as a string.
            geo_func: a function, must be GeoIP2.city or GeoIP2.country,
                used to do the IP lookup.

        Returns a GeoData object. If the address cannot be found (e.g. localhost)
            then it will still return an object that can be stashed in the session
            to prevent repeated invalid lookups. If the lookup raises any other
            exception it returns None, so that future requests _will_ repeat the lookup.

        """
        try:
            return GeoData(ip_address, **geo_func(ip_address))
        except AddressNotFoundError:
            logger.debug("IP address not found in MaxMind database: %s", ip_address)
            return GeoData.unknown_country(ip_address)
        except GeoIP2Exception:
            logger.exception("GeoIP2 exception raised for %s", ip_address)
        except Exception:
            logger.exception("Error raised looking up geoip2 data for %s", ip_address)
