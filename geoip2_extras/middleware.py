from __future__ import annotations

import logging
from typing import Callable

from django.conf import settings
from django.contrib.gis.geoip2 import GeoIP2, GeoIP2Exception
from django.core.cache import InvalidCacheBackendError, caches
from django.core.exceptions import MiddlewareNotUsed
from django.http import HttpRequest, HttpResponse
from geoip2.errors import AddressNotFoundError

logger = logging.getLogger(__name__)

GEO_CACHE_TIMEOUT = getattr(settings, "GEOIP2_EXTRAS_GEO_CACHE_TIMEOUT", 3600)


def unknown_address(ip_address: str) -> dict:
    return {"country_code": "XX", "country_name": "unknown", "remote_addr": ip_address}


def annotate_request(request: HttpRequest, data: GeoIP2) -> None:
    """Add GeoIP2 data to the Request headers."""
    for k, v in data.items():
        # request.headers is immutable, so we have to go in via META
        v = "" if v is None else v
        request.META[f"HTTP_X_GEOIP2_{k.upper().replace('-','_')}"] = v


def annotate_response(response: HttpResponse, data: GeoIP2) -> None:
    """Add GeoIP2 data to the Response headers."""
    for k, v in data.items():
        v = "" if v is None else v
        response.headers[f"X-GeoIP2-{k.title().replace('_','-')}"] = v


def remote_addr(request: HttpRequest) -> str:
    """Return client IP."""
    header = (
        request.META.get("HTTP_X_FORWARDED_FOR")
        or request.META.get("REMOTE_ADDR")
        or "0.0.0.0"  # noqa: S104
    )
    # Pick the last IP address in the list if there is one:
    # http://stackoverflow.com/a/37061471/45698
    return header.split(",")[-1].strip()


class GeoIP2Middleware:
    """
    Add GeoIP country info to each request.

    This middleware will add a `X-Geoip2-*` headers to the HttpRequest
    and HttpResponse. The exact headers added to the request/response
    depend on the information that is returned from the GeoIP2 lib for
    the request IP address. If no valid address info is returned, then
    no headers are added.

    The format of the headers follows the relevant attr name, so:

        GeoIP2.city         -> X-GeoIP-City
        GeoIP2.country_code -> X-GeoIP-Country-Code
        GeoIP2.latitude     -> X-GeoIP-Latitude

    The information is cached between requests.

    """

    # extracted to facilitate testing
    def __init_geoip2__(self) -> None:
        """Initialise GeoIP2, raise MiddlewareNotUsed on error."""
        try:
            self.geoip2 = GeoIP2()
        except GeoIP2Exception as ex:
            raise MiddlewareNotUsed(f"GeoError initialising GeoIP2: {ex}") from ex

    # extracted to facilitate testing
    def __init_cache__(self) -> None:
        """Initialise cache, raise MiddlewareNotUsed on error."""
        try:
            self.cache = caches["geoip2-extras"]
        except InvalidCacheBackendError as ex:
            raise MiddlewareNotUsed(f"GeoIP2 - cache configuration error: {ex}") from ex

    def __init__(self, get_response: Callable) -> None:
        self.__init_cache__()
        self.__init_geoip2__()
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Add GeoIP2 data to both request and response."""
        ip_address = remote_addr(request)
        geo_data = self.geo_data(ip_address)
        annotate_request(request, geo_data)
        response = self.get_response(request)
        annotate_response(response, geo_data)
        return response

    def cache_key(self, ip_address: str) -> str:
        return f"geoip2-extras::{ip_address}"

    def cache_get(self, ip_address: str) -> dict | None:
        return self.cache.get(self.cache_key(ip_address))

    def cache_set(self, ip_address: str, data: dict | None) -> None:
        if not data:
            self.cache.delete(self.cache_key(ip_address))
        else:
            self.cache.set(self.cache_key(ip_address), data, GEO_CACHE_TIMEOUT)

    def city_or_country(self, ip_address: str) -> dict:
        if self.geoip2._city:
            return self.geoip2.city(ip_address)
        if self.geoip2._country:
            return self.geoip2.country(ip_address)
        raise GeoIP2Exception("GeoIP2 has neither city nor country database")

    def geo_data(self, ip_address: str) -> dict | None:
        """
        Return GeoIP2data for an IP address.

        If AddressNotFound occurs then we return the unknown data, and cache it
        (as the IP address is not found); if the GeoIP2 lookup fails, we return
        the unknown data, but do _not_ cache it, as we want to try again on the
        next request.

        """
        data = self.cache_get(ip_address)
        if data is not None:
            logger.debug("GeoIP2 cache HIT for %s", ip_address)
            return data

        logger.debug("GeoIP2 - cache miss for %s", ip_address)
        try:
            data = self.city_or_country(ip_address)
        except AddressNotFoundError:
            logger.debug("GeoIP2 - IP address not found: %s", ip_address)
            data = unknown_address(ip_address)
        except GeoIP2Exception:
            logger.exception("GeoIP2 - exception raised for %s", ip_address)
            return None
        else:
            data["remote_addr"] = ip_address
        # we've had to look it up, so cache it
        self.cache_set(ip_address, data)
        return data
