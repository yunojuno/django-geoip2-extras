from unittest import mock

import pytest
from django.contrib.gis.geoip2 import GeoIP2, GeoIP2Exception
from django.core.cache import caches
from django.http import HttpRequest, HttpResponse
from django.test import RequestFactory, client
from geoip2.errors import AddressNotFoundError

from geoip2_extras.middleware import (
    GeoIP2Middleware,
    annotate_request,
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


# from geoip2_extras.middleware import GeoIP2Middleware
def test_annotate_request(rf: RequestFactory) -> None:
    request = rf.get("/")
    data = unknown_address("1.2.3.4")
    data["foo"] = None
    annotate_request(request, data)
    assert request.META["HTTP_X_GEOIP2_COUNTRY_CODE"] == data["country_code"]
    assert request.headers["x-geoip2-country-code"] == data["country_code"]
    assert request.META["HTTP_X_GEOIP2_FOO"] == ""
    assert request.headers["x-geoip2-foo"] == ""


# from geoip2_extras.middleware import GeoIP2Middleware
def test_annotate_response() -> None:
    response = HttpResponse()
    data = unknown_address("1.2.3.4")
    data["foo"] = None
    annotate_response(response, data)
    assert response.headers["x-geoip2-country-code"] == data["country_code"]
    assert response.headers["x-geoip2-foo"] == ""


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
    @mock.patch.object(GeoIP2Middleware, "__init_geoip2__")
    def test_geo_data__cached(
        self, mock_init_geoip, mock_set, mock_get, mock_city_or_country
    ) -> None:
        middleware = GeoIP2Middleware(lambda r: HttpResponse())
        mock_get.return_value = TEST_CITY_DATA.copy()
        result = middleware.geo_data("1.2.3.4")
        assert result == mock_get.return_value
        assert mock_set.call_count == 0
        assert mock_city_or_country.call_count == 0

    @mock.patch.object(GeoIP2Middleware, "city_or_country")
    @mock.patch.object(GeoIP2Middleware, "cache_get")
    @mock.patch.object(GeoIP2Middleware, "cache_set")
    @mock.patch.object(GeoIP2Middleware, "__init_geoip2__")
    def test_geo_data__uncached(
        self, mock_init_geoip, mock_set, mock_get, mock_city_or_country
    ) -> None:
        middleware = GeoIP2Middleware(lambda r: HttpResponse())
        mock_get.return_value = None
        mock_city_or_country.return_value = TEST_CITY_DATA.copy()
        data = mock_city_or_country.return_value
        data["remote_addr"] = "1.2.3.4"
        assert middleware.geo_data("1.2.3.4") == data
        mock_set.assert_called_once_with("1.2.3.4", data)

    @mock.patch.object(GeoIP2Middleware, "city_or_country")
    @mock.patch.object(GeoIP2Middleware, "cache_get")
    @mock.patch.object(GeoIP2Middleware, "__init_geoip2__")
    def test_geo_data__address_not_found(
        self, mock_init_geoip, mock_get, mock_city_or_country
    ) -> None:
        middleware = GeoIP2Middleware(lambda r: HttpResponse())
        mock_get.return_value = None
        mock_city_or_country.side_effect = AddressNotFoundError()
        assert middleware.geo_data("1.2.3.4") == unknown_address("1.2.3.4")

    @mock.patch.object(GeoIP2Middleware, "city_or_country")
    @mock.patch.object(GeoIP2Middleware, "cache_get")
    @mock.patch.object(GeoIP2Middleware, "__init_geoip2__")
    def test_geo_data__geoip2_exception(
        self, mock_init_geoip, mock_get, mock_city_or_country
    ) -> None:
        middleware = GeoIP2Middleware(lambda r: HttpResponse())
        mock_get.return_value = None
        mock_city_or_country.side_effect = GeoIP2Exception()
        assert middleware.geo_data("1.2.3.4") == None

    @mock.patch.object(GeoIP2Middleware, "geo_data")
    @mock.patch.object(GeoIP2Middleware, "__init_geoip2__")
    def test__call__(self, mock_geoip2, mock_geo_data, rf):
        request = rf.get("/")
        middleware = GeoIP2Middleware(lambda r: HttpResponse())
        mock_geo_data.return_value = TEST_COUNTRY_DATA.copy()
        response = middleware(request)
        assert request.headers["x-geoip2-country-code"] == "US"
        assert request.headers["x-geoip2-country-name"] == "United States"
        assert response.headers["x-geoip2-country-code"] == "US"
        assert response.headers["x-geoip2-country-name"] == "United States"

    @mock.patch.object(GeoIP2Middleware, "__init_geoip2__")
    def test_cache_set(self, mock_init_geoip):
        caches["geoip2-extras"].clear()
        middleware = GeoIP2Middleware(lambda r: HttpResponse())
        assert middleware.cache_get("1.2.3.4") is None
        middleware.cache_set("1.2.3.4", {})
        assert middleware.cache_get("1.2.3.4") is None
        middleware.cache_set("1.2.3.4", {"remote_addr": "1.2.3.4"})
        assert middleware.cache_get("1.2.3.4") == {"remote_addr": "1.2.3.4"}
