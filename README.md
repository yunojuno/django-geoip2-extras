# Django GeoIP2 Extras

Useful extras based on the `django.contrib.gis.geoip2` module, using
the [MaxMind GeoIP2 Lite](http://dev.maxmind.com/geoip/geoip2/geolite2/) database.

The first feature in this package is a Django middleware class that can
be used to add city, country level information to inbound requests.

### Version support

The current version of the this app support **Python 3.8+** and **Django 3.2+**

## Requirements

1) This package wraps the existing Django functionality, and as a result
relies on the same underlying requirements:

    In order to perform IP-based geolocation, the GeoIP2 object
    requires the geoip2 Python library and the GeoIP Country and/or City
    datasets in binary format (the CSV files will not work!). Grab the
    GeoLite2-Country.mmdb.gz and GeoLite2-City.mmdb.gz files and unzip
    them in a directory corresponding to the GEOIP_PATH setting.

NB: The MaxMind database is not included with this package. It is your
responsiblity to download this and include it as part of your project.

2) This package requires the usage of a Django cache configuration to
maintain adaquate performance.


## Installation

This package can be installed from PyPI as `django-geoip2-extras`:

```
$ pip install django-geoip2-extras
```

If you want to add the country-level information to incoming requests,
add the middleware to your project settings.

```python
# settings.py
MIDDLEWARE = (
    ...,
    'geoip2_extras.middleware.GeoIP2Middleware',
)
```

The middleware will not be active unless you add a setting for the
default `GEOIP_PATH` - this is the default Django GeoIP2 behaviour:

```python
# settings.py
GEOIP_PATH = os.path.dirname(__file__)
```

You must also configure a cache to use  via `GEOIP2_EXTRAS_CACHE_NAME`.
The value should match the name of the Django cache configuration you
wish to use for caching.

```python
# settings.py

# Django cache configuration setting
CACHES = {
    "default": { ... },
    "some-other-cache": { ... },  # <-- it would use this one.
    ...
}

# Set this to specific configuration name from CACHES
GEOIP2_EXTRAS_CACHE_NAME = "some-other-cache"
```

Tip: see `/demo/settings.py` for a full working example.

### Settings

The following settings can be overridden via your Django settings:

* `GEOIP2_EXTRAS_CACHE_NAME`

The Django cache configuration to use for cacheing.

* `GEOIP2_EXTRAS_CACHE_TIMEOUT`

Time to cache IP <> address data in seconds - default to 1hr (3600s)

* `GEOIP2_EXTRAS_ADD_RESPONSE_HEADERS`

Set to True to write out the GeoIP data to the response headers. Defaults to use
the `DEBUG` value. This value can be overridden on a per-request basis by adding
the `X-GeoIP2-Debug` request header, or adding `geoip2=1` to the request
querystring. This is useful for debugging in a production environment where you
may not be adding the response headers by default.

## Usage

Once the middleware is added, you will be able to access City and / or
Country level information on the request object via the `geo_data` dict:

```python
>>> request.geo_data
{
    "city": ""
    "continent-code": "NA"
    "continent-name": "North America"
    "country-code": "US"
    "country-name": "United States"
    "dma-code": ""
    "is-in-european-union": False
    "latitude": 37.751
    "longitude": -97.822
    "postal-code": ""
    "region": ""
    "time-zone": "America/Chicago"
    "remote-addr": "142.250.180.3"
}
```

The same information will be added to the HttpResponse headers if
`GEOIP2_EXTRAS_ADD_RESPONSE_HEADERS` is True. Values are set using the
`X-GeoIP2-` prefix.

NB blank (`""`) values are **not** added to the response:

```shell
# use the google.co.uk IP
$ curl -I -H "x-forwarded-for: 142.250.180.3" localhost:8000
HTTP/1.1 200 OK
Date: Sun, 29 Aug 2021 15:47:22 GMT
Server: WSGIServer/0.2 CPython/3.9.4
Content-Type: text/html
X-GeoIP2-Continent-Code: NA
X-GeoIP2-Continent-Name: North America
X-GeoIP2-Country-Code: US
X-GeoIP2-Country-Name: United States
X-GeoIP2-Is-In-European-Union: False
X-GeoIP2-Latitude: 37.751
X-GeoIP2-Longitude: -97.822
X-GeoIP2-Time-Zone: America/Chicago
X-GeoIP2-Remote-Addr: 142.250.180.3
Content-Length: 10697
```

If the IP address cannot be found (e.g. '127.0.0.1'), then a default
'unknown' country is used, with a code of 'XX'.

```shell
$ curl -I -H "x-forwarded-for: 127.0.0.1" localhost:8000
HTTP/1.1 200 OK
Date: Sun, 29 Aug 2021 15:47:22 GMT
Server: WSGIServer/0.2 CPython/3.9.4
Content-Type: text/html
X-GeoIP2-Country-Code: XX
X-GeoIP2-Country-Name: unknown
X-GeoIP2-Remote-Addr: 127.0.0.1
Content-Length: 10697
```

## Tests

The project tests are run through `pytest`.
