from unittest import mock

from django.contrib.gis.geoip2 import GeoIP2, GeoIP2Exception
from django.core.exceptions import MiddlewareNotUsed
from django.test import TestCase, override_settings
from geoip2.database import Reader

from geoip2_extras.middleware import (
    GeoIP2Middleware,
    AddressNotFoundError,
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

    @mock.patch('geoip2_extras.middleware.GeoIP2')
    def test_init(self, mock_geo2):
        get_response = lambda x: x
        middleware = GeoIP2Middleware(get_response)
        self.assertEqual(middleware.get_response, get_response)

        # mock out a GeoIP2 with no _reader set - mimics the case
        # when neither country nor city databases exist.
        mock_geo2.return_value._reader = None
        self.assertRaises(
            MiddlewareNotUsed,
            GeoIP2Middleware,
            get_response
        )

        # now force a known exception in the init
        mock_geo2.return_value._reader = mock.Mock(spec=Reader)
        mock_geo2.side_effect = GeoIP2Exception()
        self.assertRaises(
            MiddlewareNotUsed,
            GeoIP2Middleware,
            get_response
        )
