**The master branch of this project is now Python 3.7+ and Django 3.2+ only. Legacy Python and Django versions are tagged.**

# Django GeoIP2 Extras

Useful extras based on the `django.contrib.gis.geoip2` module, using
the [MaxMind GeoIP2 Lite](http://dev.maxmind.com/geoip/geoip2/geolite2/) database.

The first feature in this package is a Django middleware class that can
be used to add city, country level information to inbound requests.

## Requirements

This package wraps the existing Django functionality, and as a result
relies on the same underlying requirements:

    In order to perform IP-based geolocation, the GeoIP2 object
    requires the geoip2 Python library and the GeoIP Country and/or City
    datasets in binary format (the CSV files will not work!). Grab the
    GeoLite2-Country.mmdb.gz and GeoLite2-City.mmdb.gz files and unzip
    them in a directory corresponding to the GEOIP_PATH setting.

This package requires Django 3.2 or above.

## Installation

This package can be installed from PyPI as `django-geoip2-extras`:

```
$ pip install django-geoip2-extras
```

If you want to add the country-level information to incoming requests,
add the middleware to your project settings. NB The ``GeoIP2Middleware``
relies on the ``SessionMiddleware``, and must come after it:

```python
# settings.py
MIDDLEWARE = (
    ...,
    'django.contrib.sessions.middleware.SessionMiddleware',
    'geoip2_extras.middleware.GeoIP2Middleware',
    ...
)
```

The middleware will not be active unless you add a setting for
the default `GEOIP_PATH` - this is the default Django GeoIP2 behaviour:

```python
# settings.py
GEOIP_PATH = os.path.dirname(__file__)
```

NB Loading this package does *not* install the (MaxMind
database)[<http://dev.maxmind.com/geoip/geoip2/geolite2/]. That is your
responsibility. The Country database is 2.7MB, and could be added to
most project comfortably, but it is updated regularly, and keeping that
up-to-date is out of scope for this project. The City database is 27MB,
and is probably not suitable for adding to source control. There are
various solutions out on the web for pulling in the City database as
part of a CD process.

Usage
=====

Once the middleware is added, you will be able to access City and / or Country level
information on the request object:

```python
>>> request.headers["x-geoip2-city"]
'Beverley Hills'
>>> request.headers["x-geoip2-postal_code"]
'90210'
>>> request.headers["x-geoip2-region"]
'California'
>>> request.headers["x-geoip2-country_code"]
'US'
>>> request.headers["x-geoip2-country_name"]
'United States'
>>> request.headers["x-geoip2-latitude"]
'34.0736'
>>> request.headers["x-geoip2-longitude"]
'118.4004'
```

Missing / incomplete data will be "".

If the IP address cannot be found (e.g. '127.0.0.1'), then a default 'unknown'
country is used, with a code of 'XX':

## Tests

The project tests are run through `pytest`.
