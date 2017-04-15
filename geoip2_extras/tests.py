# -*- coding: utf-8 -*-
import mock

from django.contrib.gis.geoip2 import GeoIP2, GeoIP2Exception
from django.core.exceptions import MiddlewareNotUsed
from django.test import TestCase, override_settings

from .middleware import GeoIP2Middleware


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

    def test_get_remote_addr(self):
        request = mock.Mock()
        request.META = {
            'REMOTE_ADDR': '1.2.3.4'
        }
        self.assertEqual(self.middleware.get_remote_addr(request), '1.2.3.4')
        request.META['HTTP_X_FORWARDED_FOR'] = '8.8.8.8'
        self.assertEqual(self.middleware.get_remote_addr(request), '8.8.8.8')
        request.META['HTTP_X_FORWARDED_FOR'] = '1.2.3.4,8.8.8.8'
        self.assertEqual(self.middleware.get_remote_addr(request), '8.8.8.8')

    @mock.patch.object(GeoIP2, 'country')
    def test_get_country(self, mock_country):
        mock_country.return_value = self.test_country
        country = self.middleware.get_country(self.test_ip)
        self.assertEqual(country['ip_address'], '8.8.8.8')
        self.assertEqual(country['country_code'], 'GB')
        self.assertEqual(country['country_name'], 'United Kingdom')

        mock_country.side_effect = Exception()
        country = self.middleware.get_country(self.test_ip)
        self.assertIsNone(country)

    @mock.patch.object(GeoIP2, 'country')
    def test_get_session_data(self, mock_country):
        request = mock.Mock()
        request.META = {'REMOTE_ADDR': self.test_ip}
        request.session = {}
        mock_country.return_value = self.test_country

        # test: clean session
        retval = self.test_country
        retval['ip_address'] = self.test_ip
        country = self.middleware.get_session_data(request)
        mock_country.assert_called_with(self.test_ip)
        self.assertEqual(country, retval)

        # test: object in session does not match current IP
        request.session[GeoIP2Middleware.SESSION_KEY] = self.test_country
        request.session[GeoIP2Middleware.SESSION_KEY]['ip_address'] = '1.2.3.4'
        country = self.middleware.get_session_data(request)
        mock_country.assert_called_with(self.test_ip)
        self.assertEqual(country, retval)

        # test: session object is up-to-date
        request.session[GeoIP2Middleware.SESSION_KEY]['ip_address'] = request.META['REMOTE_ADDR']
        mock_country.reset_mock()
        country = self.middleware.get_session_data(request)
        mock_country.assert_not_called()

    @mock.patch.object(GeoIP2Middleware, 'get_session_data')
    def test_middleware_call(self, mock_country):
        middleware = GeoIP2Middleware(lambda r: None)
        request = mock.Mock(session={})
        middleware(request)
        mock_country.assert_called_once_with(request)
        self.assertEqual(request.country, mock_country.return_value)
        self.assertEqual(
            request.session[GeoIP2Middleware.SESSION_KEY],
            mock_country.return_value
        )

    @mock.patch('geoip2_extras.middleware.GeoIP2')
    def test_init(self, mock_geo2):
        """Test we can switch off the middleware using waffle."""

        # test: switch off should disable middleware
        with override_settings(GEOIP2_MIDDLEWARE_ENABLED=False):
            self.assertRaises(
                MiddlewareNotUsed,
                GeoIP2Middleware,
                GeoIP2MiddlewareTests.get_response
            )

        # test: switch ON, should set up geoip
        with override_settings(GEOIP2_MIDDLEWARE_ENABLED=True):
            middleware = GeoIP2Middleware(GeoIP2MiddlewareTests.get_response)
            self.assertEqual(middleware.get_response, GeoIP2MiddlewareTests.get_response)

            # test: switch ON, but GeoIP2 can't be initialised
            mock_geo2.side_effect = GeoIP2Exception('Foo')
            self.assertRaises(
                MiddlewareNotUsed,
                GeoIP2Middleware,
                GeoIP2MiddlewareTests.get_response
            )
