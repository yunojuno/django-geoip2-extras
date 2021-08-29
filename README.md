# Django GeoIP2 Extras

Useful extras based on the `django.contrib.gis.geoip2` module, using
the [MaxMind GeoIP2 Lite](http://dev.maxmind.com/geoip/geoip2/geolite2/) database.

The first feature in this package is a Django middleware class that can
be used to add city, country level information to inbound requests.

## Requirements

This package requires Django 2.2 or above, and Python 3.7 or above.

This package wraps the existing Django functionality, and as a result
relies on the same underlying requirements:

    In order to perform IP-based geolocation, the GeoIP2 object
    requires the geoip2 Python library and the GeoIP Country and/or City
    datasets in binary format (the CSV files will not work!). Grab the
    GeoLite2-Country.mmdb.gz and GeoLite2-City.mmdb.gz files and unzip
    them in a directory corresponding to the GEOIP_PATH setting.

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

NB Loading this package does *not* install the (MaxMind
database)[http://dev.maxmind.com/geoip/geoip2/geolite2/]. That is your
responsibility. The Country database is 2.7MB, and could be added to
most project comfortably, but it is updated regularly, and keeping that
up-to-date is out of scope for this project. The City database is 27MB,
and is probably not suitable for adding to source control. There are
various solutions out on the web for pulling in the City database as
part of a CD process.

## Usage

Once the middleware is added, you will be able to access City and / or
Country level information on the request object via the `geo_data` dict,
and the same information will be added to the HttpResponse headers.

The raw data is added to the response headers thus:

```
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

This is available from your code via the `request.geo_data` dict:

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

Missing / incomplete data will **not** be included in the response headers.

If the IP address cannot be found (e.g. '127.0.0.1'), then a default
'unknown' country is used, with a code of 'XX'.

## Tests

The project tests are run through `pytest`.
