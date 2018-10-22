from unittest import mock

from django.contrib.gis.geoip2 import GeoIP2, GeoIP2Exception
from django.core.exceptions import MiddlewareNotUsed
from django.http import HttpRequest
from django.test import TestCase, override_settings
from geoip2.database import Reader

from geoip2_extras.middleware import (
    GeoIP2Middleware,
    GeoIP2Exception,
    AddressNotFoundError,
    remote_addr,
    unknown_address
)


@override_settings(GEOIP2_MIDDLEWARE_ENABLED=True)
class GeoIP2MiddlewareTests(TestCase):

    # fix for django GeoIP2 bug
    @mock.patch.object(GeoIP2, '_reader', mock.Mock(Reader))
    def setUp(self):
        self.middleware = GeoIP2Middleware(lambda x: x)
        self.test_ip = '8.8.8.8'
        self.test_country_data = {
            'country_code': 'GB',
            'country_name': 'United Kingdom'
        }
        self.test_city_data = {
            'city': 'Los Angeles',
            'country_code': 'US',
            'country_name': 'United States',
            'dma_code': None,
            'latitude': 37.751,
            'longitude': -97.822,
            'postal_code': 90210,
            'region': 'CA'
        }
        self.unknown_address = unknown_address(self.test_ip)
        self.middleware.cache.clear()

    @mock.patch('geoip2_extras.middleware.GeoIP2')
    def test__init(self, mock_geo2):
        get_response = lambda x: x
        middleware = GeoIP2Middleware(get_response)
        self.assertEqual(middleware.get_response, get_response)

    @override_settings(CACHES={
        'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}
    })
    def test__init__cache_missing(self):
        """No available GeoIP2 cache - middleware is disabled."""
        get_response = lambda x: x
        self.assertRaises(MiddlewareNotUsed, GeoIP2Middleware, get_response)

    @mock.patch('geoip2_extras.middleware.GeoIP2')
    def test__init__no_reader(self, mock_geo2):
        """No available GeoIP2 reader - middleware is disabled."""
        get_response = lambda x: x
        mock_geo2.return_value._reader = None
        self.assertRaises(MiddlewareNotUsed, GeoIP2Middleware, get_response)

    @mock.patch('geoip2_extras.middleware.GeoIP2')
    def test__init__reader_error(self, mock_geo2):
        """Generic GeoIP2 raised - middleware is disabled."""
        get_response = lambda x: x
        # now force a known exception in the init
        mock_geo2.return_value._reader = mock.Mock(spec=Reader)
        mock_geo2.side_effect = GeoIP2Exception()
        self.assertRaises(MiddlewareNotUsed, GeoIP2Middleware, get_response)

    @mock.patch('geoip2_extras.middleware.remote_addr')
    @mock.patch.object(GeoIP2Middleware, 'geo_data')
    @mock.patch('geoip2_extras.middleware.GeoIP2')
    def test__call(self, mock_geoip2, mock_geo_data, mock_remote_addr):
        """Calling middleware sets the remote_addr and geo_data properties."""
        request = mock.Mock(spec=HttpRequest)
        assert hasattr(request, 'remote_addr') is False
        assert hasattr(request, 'geo_data') is False
        self.middleware(request)
        assert request.remote_addr == mock_remote_addr.return_value
        assert request.geo_data == mock_geo_data.return_value

    def test_geo_data__cache_hit(self):
        test_geo = {'country_code': 'foo', 'country_name': 'bar'}
        self.middleware.cache.set(self.test_ip, test_geo)
        assert self.middleware.geo_data(self.test_ip) == test_geo

    @mock.patch.object(GeoIP2Middleware, '_city_or_country')
    def test_geo_data__cache_miss_address_found(self, mock_city):
        mock_city.return_value = self.test_city_data
        assert self.middleware.geo_data(self.test_ip) == self.test_city_data

    @mock.patch.object(GeoIP2Middleware, '_city_or_country')
    def test_geo_data__cache_miss_address_not_found(self, mock_city):
        mock_city.side_effect = AddressNotFoundError()
        geo_data = self.middleware.geo_data(self.test_ip)
        assert geo_data == self.unknown_address

    @mock.patch.object(GeoIP2Middleware, '_city_or_country')
    def test_geo_data__cache_miss_geoip2_error(self, mock_city):
        mock_city.side_effect = GeoIP2Exception()
        geo_data = self.middleware.geo_data(self.test_ip)
        assert geo_data is None

    @mock.patch.object(GeoIP2Middleware, '_city_or_country')
    def test_geo_data__cache_miss_unhandled_error(self, mock_city):
        mock_city.side_effect = Exception()
        self.assertRaises(Exception, self.middleware.geo_data, self.test_ip)

    @mock.patch.object(GeoIP2, '_city', True)
    @mock.patch.object(GeoIP2, 'country')
    @mock.patch.object(GeoIP2, 'city')
    def test__city_or_country__city_data(self, mock_city, mock_country):
        data = self.middleware._city_or_country(self.test_ip)
        mock_city.call_count == 1
        mock_country.call_count == 0
        assert data == mock_city.return_value

    @mock.patch.object(GeoIP2, '_city', False)
    @mock.patch.object(GeoIP2, 'country')
    @mock.patch.object(GeoIP2, 'city')
    def test__city_or_country__country_data(self, mock_city, mock_country):
        data = self.middleware._city_or_country(self.test_ip)
        mock_city.call_count == 0
        mock_country.call_count == 1
        assert data == mock_country.return_value


class GeoIP2MiddlewareFunctionTests(TestCase):


    def test_unknown_address(self):
        data = unknown_address('8.8.8.8')
        assert data['remote_addr'] == '8.8.8.8'
        assert data['country_code'] == 'XX'
        assert data['country_name'] == 'unknown'

    def test_remote_addr(self):
        request = mock.Mock(META={})
        assert remote_addr(request) == '0.0.0.0'
        request.META['REMOTE_ADDR'] = '1.2.3.4'
        assert remote_addr(request) == '1.2.3.4'
        request.META['HTTP_X_FORWARDED_FOR'] = '8.8.8.8'
        assert remote_addr(request) == '8.8.8.8'
        request.META['HTTP_X_FORWARDED_FOR'] = '1.2.3.4,8.8.8.8'
        assert remote_addr(request) == '8.8.8.8'
        request.META['HTTP_X_FORWARDED_FOR'] = None
        assert remote_addr(request) == '1.2.3.4'
        request.META['REMOTE_ADDR'] = None
        assert remote_addr(request) == '0.0.0.0'
