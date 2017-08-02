# -*- coding: utf-8 -*-
import mock

from django.contrib.gis.geoip2 import GeoIP2, GeoIP2Exception
from django.core.exceptions import MiddlewareNotUsed
from django.test import TestCase, override_settings

from .middleware import (
    GeoIP2Middleware,
    AddressNotFoundError
)


@override_settings(GEOIP2_MIDDLEWARE_ENABLED=True)
class GeoIP2MiddlewareTests(TestCase):

    def get_response():
        pass

    def setUp(self):
        self.middleware = GeoIP2Middleware(GeoIP2MiddlewareTests.get_response)
        self.test_ip = '8.8.8.8'
        self.test_country = {
            'country_code': 'GB',
            'country_name': 'United Kingdom'
        }

    def test_remote_addr(self):
        request = mock.Mock(META={})
        self.assertEqual(self.middleware.remote_addr(request), '0.0.0.0')
        request.META = {
            'REMOTE_ADDR': '1.2.3.4'
        }
        self.assertEqual(self.middleware.remote_addr(request), '1.2.3.4')
        request.META['HTTP_X_FORWARDED_FOR'] = '8.8.8.8'
        self.assertEqual(self.middleware.remote_addr(request), '8.8.8.8')
        request.META['HTTP_X_FORWARDED_FOR'] = '1.2.3.4,8.8.8.8'
        self.assertEqual(self.middleware.remote_addr(request), '8.8.8.8')
        request.META['HTTP_X_FORWARDED_FOR'] = None
        self.assertEqual(self.middleware.remote_addr(request), '1.2.3.4')
        request.META['REMOTE_ADDR'] = None
        self.assertEqual(self.middleware.remote_addr(request), '0.0.0.0')

    @mock.patch.object(GeoIP2, 'country')
    def test_country(self, mock_country):
        mock_country.return_value = self.test_country
        country = self.middleware.country(self.test_ip)
        self.assertEqual(country['ip_address'], '8.8.8.8')
        self.assertEqual(country['country_code'], 'GB')
        self.assertEqual(country['country_name'], 'United Kingdom')

        mock_country.side_effect = AddressNotFoundError()
        country = self.middleware.country(self.test_ip)
        self.assertEqual(country['ip_address'], '8.8.8.8')
        self.assertEqual(country['country_code'], GeoIP2Middleware.UNKNOWN_COUNTRY_CODE)
        self.assertEqual(country['country_name'], GeoIP2Middleware.UNKNOWN_COUNTRY_NAME)

        mock_country.side_effect = Exception()
        country = self.middleware.country(self.test_ip)
        self.assertIsNone(country)

    @mock.patch.object(GeoIP2Middleware, 'country')
    def test_middleware_call(self, mock_country):
        middleware = GeoIP2Middleware(lambda r: None)
        request = mock.Mock()
        request.META = {'REMOTE_ADDR': self.test_ip}

        # test: clean session
        request.session = {}
        middleware(request)
        mock_country.assert_called_with(self.test_ip)
        self.assertEqual(request.country, mock_country.return_value)
        self.assertEqual(request.session[GeoIP2Middleware.SESSION_KEY], mock_country.return_value)

        # test: object in session does not match current IP
        mock_country.reset_mock()
        request.session[GeoIP2Middleware.SESSION_KEY] = self.test_country
        request.session[GeoIP2Middleware.SESSION_KEY]['ip_address'] = '1.2.3.4'
        middleware(request)
        mock_country.assert_called_with(self.test_ip)
        self.assertEqual(request.country, mock_country.return_value)
        self.assertEqual(request.session[GeoIP2Middleware.SESSION_KEY], mock_country.return_value)

        # test: session object is up-to-date
        mock_country.reset_mock()
        request.session[GeoIP2Middleware.SESSION_KEY] = self.test_country
        request.session[GeoIP2Middleware.SESSION_KEY]['ip_address'] = self.test_ip
        middleware(request)
        mock_country.assert_not_called()

    @mock.patch('geoip2_extras.middleware.GeoIP2')
    def test_init(self, mock_geo2):
        middleware = GeoIP2Middleware(GeoIP2MiddlewareTests.get_response)
        self.assertEqual(middleware.get_response, GeoIP2MiddlewareTests.get_response)
        # test: GeoIP2 can't be initialised
        mock_geo2.side_effect = GeoIP2Exception()
        self.assertRaises(
            MiddlewareNotUsed,
            GeoIP2Middleware,
            GeoIP2MiddlewareTests.get_response
        )
