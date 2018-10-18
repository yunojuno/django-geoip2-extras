from unittest import mock

from django.contrib.gis.geoip2 import GeoIP2, GeoIP2Exception
from django.core.exceptions import MiddlewareNotUsed
from django.test import TestCase, override_settings

from geoip2.database import Reader

from .middleware import (
    GeoIP2Middleware,
    GeoData,
    AddressNotFoundError
)


class GeoDataTests(TestCase):

    def test_is_unknown(self):
        geo = GeoData('8.8.8.8')
        self.assertFalse(geo.is_unknown)
        geo.country_code = GeoData.UNKNOWN_COUNTRY_CODE
        self.assertTrue(geo.is_unknown)


@override_settings(GEOIP2_MIDDLEWARE_ENABLED=True)
class GeoIP2MiddlewareTests(TestCase):

    def get_response():
        pass

    # fix for django GeoIP2 bug
    @mock.patch.object(GeoIP2, '_reader', mock.Mock(Reader))
    def setUp(self):
        self.middleware = GeoIP2Middleware(GeoIP2MiddlewareTests.get_response)
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
        self.test_country = GeoData(self.test_ip, **self.test_country_data)
        self.test_city = GeoData(self.test_ip, **self.test_city_data)

    def test_remote_addr(self):
        request = mock.Mock(META={})
        self.assertEqual(self.middleware.remote_addr(request), '0.0.0.0')
        request.META['REMOTE_ADDR'] = '1.2.3.4'
        self.assertEqual(self.middleware.remote_addr(request), '1.2.3.4')
        request.META['HTTP_X_FORWARDED_FOR'] = '8.8.8.8'
        self.assertEqual(self.middleware.remote_addr(request), '8.8.8.8')
        request.META['HTTP_X_FORWARDED_FOR'] = '1.2.3.4,8.8.8.8'
        self.assertEqual(self.middleware.remote_addr(request), '8.8.8.8')
        request.META['HTTP_X_FORWARDED_FOR'] = None
        self.assertEqual(self.middleware.remote_addr(request), '1.2.3.4')
        request.META['REMOTE_ADDR'] = None
        self.assertEqual(self.middleware.remote_addr(request), '0.0.0.0')

    @mock.patch.object(GeoIP2Middleware, '_geoip2')
    def test_geo_data(self, mock__geoip2):
        """Check that city / country routing works."""
        self.middleware.geoip2 = mock.Mock(_city=True)
        self.middleware.geo_data(self.test_ip)
        mock__geoip2.assert_called_with(self.test_ip, self.middleware.geoip2.city)

        self.middleware.geoip2 = mock.Mock(_city=None)
        self.middleware.geo_data(self.test_ip)
        mock__geoip2.assert_called_with(self.test_ip, self.middleware.geoip2.country)

    @mock.patch.object(GeoIP2, 'city')
    def test__geoip2(self, mock_city):
        mock_city.return_value = self.test_city_data
        data = self.middleware._geoip2(self.test_ip, mock_city)
        self.assertEqual(data, self.test_city_data)
        mock_city.side_effect = AddressNotFoundError()
        data = self.middleware.city(self.test_ip)
        self.assertEqual(data, GeoData.unknown_country(self.test_ip).__dict__)

        mock_city.side_effect = GeoIP2Exception()
        self.assertIsNone(self.middleware.city(self.test_ip))

        mock_city.side_effect = Exception()
        self.assertIsNone(self.middleware.city(self.test_ip))

    # fix for django GeoIP2 bug
    @mock.patch.object(GeoIP2, '_reader', mock.Mock(Reader))
    @mock.patch.object(GeoIP2Middleware, 'country')
    def test_middleware_call(self, mock_country):
        middleware = GeoIP2Middleware(lambda r: None)
        request = mock.Mock(META={'REMOTE_ADDR': self.test_ip})
        mock_country.return_value = self.test_country_data

        # test: clean session
        request.session = {}
        middleware(request)
        mock_country.assert_called_with(self.test_ip)
        self.assertEqual(request.geo_data, self.test_country)
        self.assertEqual(request.session[GeoIP2Middleware.SESSION_KEY], mock_country.return_value)

        # test: object in session does not match current IP
        mock_country.reset_mock()
        request.session[GeoIP2Middleware.SESSION_KEY] = self.test_city_data
        request.session[GeoIP2Middleware.SESSION_KEY]['ip_address'] = '1.2.3.4'
        middleware(request)
        mock_country.assert_called_with(self.test_ip)
        self.assertEqual(request.geo_data, self.test_country)
        self.assertEqual(request.session[GeoIP2Middleware.SESSION_KEY], mock_country.return_value)

        # test: session object is up-to-date
        mock_country.reset_mock()
        request.session[GeoIP2Middleware.SESSION_KEY] = self.test_city_data
        request.session[GeoIP2Middleware.SESSION_KEY]['ip_address'] = self.test_ip
        middleware(request)
        mock_country.assert_not_called()

    @mock.patch('geoip2_extras.middleware.GeoIP2')
    def test_init(self, mock_geo2):
        middleware = GeoIP2Middleware(GeoIP2MiddlewareTests.get_response)
        self.assertEqual(middleware.get_response, GeoIP2MiddlewareTests.get_response)

        # mock out a GeoIP2 with no _reader set - mimics the case
        # when neither country nor city databases exist.
        mock_geo2.return_value._reader = None
        self.assertRaises(
            MiddlewareNotUsed,
            GeoIP2Middleware,
            GeoIP2MiddlewareTests.get_response
        )

        # now force a known exception in the init
        mock_geo2.return_value._reader = mock.Mock(spec=Reader)
        mock_geo2.side_effect = GeoIP2Exception()
        self.assertRaises(
            MiddlewareNotUsed,
            GeoIP2Middleware,
            GeoIP2MiddlewareTests.get_response
        )
