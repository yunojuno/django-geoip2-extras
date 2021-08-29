from unittest import mock

import pytest
from django.contrib.gis.geoip2 import GeoIP2Exception
from django.core.cache import caches
from django.http import HttpResponse
from django.test import RequestFactory
from geoip2.errors import AddressNotFoundError

from geoip2_extras.middleware import (
    UNKNOWN_COUNTRY,
    GeoIP2Middleware,
    annotate_response,
    remote_addr,
    unknown_address,
)

TEST_CITY_DATA = {
    "city": None,
    "continent_code": "NA",
    "continent_name": "North America",
    "country_code": "US",
    "country_name": "United States",
    "dma_code": None,
    "is_in_european_union": False,
    "latitude": 37.751,
    "longitude": -97.822,
    "postal_code": None,
    "region": None,
    "time_zone": "America/Chicago",
}
TEST_COUNTRY_DATA = {
    "country_code": "US",
    "country_name": "United States",
}


def test_annotate_response() -> None:
    response = HttpResponse()
    data = unknown_address("1.2.3.4")
    annotate_response(response, data)
    assert response["x-geoip2-country-code"] == UNKNOWN_COUNTRY["country_code"]
    assert response["x-geoip2-country-name"] == UNKNOWN_COUNTRY["country_name"]
    assert response["x-geoip2-remote-addr"] == "1.2.3.4"


@pytest.mark.parametrize(
    "key,val,in_response",
    [("foo", None, False), ("foo", "", False), ("foo", "bar", True)],
)
def test_annotate_response__empty(key, val, in_response) -> None:
    """Test that empty fields are not added to response headers."""
    response = HttpResponse()
    annotate_response(response, {key: val})
    assert (f"x-geoip2-{key}" in response) == in_response


@pytest.mark.parametrize(
    "forwarded_ip,client_ip,result",
    [
        (None, None, "0.0.0.0"),
        ("1.2.3.4", None, "1.2.3.4"),
        ("1.2.3.4", "", "1.2.3.4"),
        ("1.2.3.4", "8.8.8.8", "1.2.3.4"),
        ("", "8.8.8.8", "8.8.8.8"),
        (None, "8.8.8.8", "8.8.8.8"),
        ("1.2.3.4,8.8.8.8", "", "8.8.8.8"),
        ("1.2.3.4,8.8.8.8", "5.6.7.8", "8.8.8.8"),
        ("1.2.3.4, 8.8.8.8 ", "5.6.7.8", "8.8.8.8"),
    ],
)
def test_remote_addr(rf: RequestFactory, forwarded_ip, client_ip, result) -> None:
    request = rf.get("/")
    request.META["REMOTE_ADDR"] = client_ip
    request.META["HTTP_X_FORWARDED_FOR"] = forwarded_ip
    assert remote_addr(request) == result


class TestGeoIP2Middleware:
    @mock.patch.object(GeoIP2Middleware, "city_or_country")
    @mock.patch.object(GeoIP2Middleware, "cache_get")
    @mock.patch.object(GeoIP2Middleware, "cache_set")
    def test_geo_data__cached(self, mock_set, mock_get, mock_city_or_country) -> None:
        middleware = GeoIP2Middleware(lambda r: HttpResponse())
        mock_get.return_value = TEST_CITY_DATA.copy()
        result = middleware.geo_data("1.2.3.4")
        assert result == mock_get.return_value
        assert mock_set.call_count == 0
        assert mock_city_or_country.call_count == 0

    @mock.patch.object(GeoIP2Middleware, "city_or_country")
    @mock.patch.object(GeoIP2Middleware, "cache_get")
    @mock.patch.object(GeoIP2Middleware, "cache_set")
    def test_geo_data__uncached(self, mock_set, mock_get, mock_city_or_country) -> None:
        middleware = GeoIP2Middleware(lambda r: HttpResponse())
        mock_get.return_value = None
        mock_city_or_country.return_value = TEST_CITY_DATA.copy()
        data = mock_city_or_country.return_value
        data["remote_addr"] = "1.2.3.4"
        assert middleware.geo_data("1.2.3.4") == data
        mock_set.assert_called_once_with("1.2.3.4", data)

    @mock.patch.object(GeoIP2Middleware, "city_or_country")
    @mock.patch.object(GeoIP2Middleware, "cache_get")
    def test_geo_data__address_not_found(self, mock_get, mock_city_or_country) -> None:
        middleware = GeoIP2Middleware(lambda r: HttpResponse())
        mock_get.return_value = None
        mock_city_or_country.side_effect = AddressNotFoundError()
        assert middleware.geo_data("1.2.3.4") == unknown_address("1.2.3.4")

    @mock.patch.object(GeoIP2Middleware, "city_or_country")
    @mock.patch.object(GeoIP2Middleware, "cache_get")
    def test_geo_data__geoip2_exception(self, mock_get, mock_city_or_country) -> None:
        middleware = GeoIP2Middleware(lambda r: HttpResponse())
        mock_get.return_value = None
        mock_city_or_country.side_effect = GeoIP2Exception()
        assert middleware.geo_data("1.2.3.4") == None

    @mock.patch.object(GeoIP2Middleware, "geo_data")
    def test__call__(self, mock_geo_data, rf):
        request = rf.get("/")
        middleware = GeoIP2Middleware(lambda r: HttpResponse())
        mock_geo_data.return_value = TEST_COUNTRY_DATA.copy()
        response = middleware(request)
        assert request.geo_data["country_code"] == "US"
        assert request.geo_data["country_name"] == "United States"
        assert response["x-geoip2-country-code"] == "US"
        assert response["x-geoip2-country-name"] == "United States"

    def test_cache_set(self):
        caches["geoip2-extras"].clear()
        middleware = GeoIP2Middleware(lambda r: HttpResponse())
        assert middleware.cache_get("1.2.3.4") is None
        middleware.cache_set("1.2.3.4", {})
        assert middleware.cache_get("1.2.3.4") is None
        middleware.cache_set("1.2.3.4", {"remote_addr": "1.2.3.4"})
        assert middleware.cache_get("1.2.3.4") == {"remote_addr": "1.2.3.4"}
