.. image:: https://badge.fury.io/py/django-geoip2-extras.svg
    :target: https://badge.fury.io/py/django-geoip2-extras

.. image:: https://travis-ci.org/yunojuno/django-geoip2-extras.svg
    :target: https://travis-ci.org/yunojuno/django-geoip2-extras

Django GeoIP2 Extras
--------------------

Useful extras based on the ``django.contrib.gis.geoip2`` package, using
the `MaxMind GeoIP2 Lite <http://dev.maxmind.com/geoip/geoip2/geolite2/>`_ database.

The first feature in this package is a Django middleware class that can
be used to add country level information to inbound requests.

Requirements
============

This package wraps the existing Django functionality, and as a result
relies on the same underlying requirements:

    *In order to perform IP-based geolocation, the GeoIP2 object requires the geoip2 Python library and the GeoIP Country and/or City datasets in binary format (the CSV files will not work!). Grab the GeoLite2-Country.mmdb.gz and GeoLite2-City.mmdb.gz files and unzip them in a directory corresponding to the GEOIP_PATH setting.*

Installation
============

This package can be installed from PyPI as ``django-geoip2-extras``:

.. code:: shell

    $ pip install django-geoip2-extras

If you want to add the country-level information to incoming requests, add the
middleware to your project settings. NB The ``GeoIP2Middleware`` relies on the ``SessionMiddleware``:

.. code:: python

    MIDDLEWARE = (
        'django.middleware.common.CommonMiddleware',
        'django.contrib.sessions.middleware.SessionMiddleware',
        'geoip2_extras.middleware.GeoIP2Middleware',
    )

The middleware will not be active unless you add a setting for
the default ``GEOIP_PATH``, and activate the middleware:

.. code:: python

    GEOIP_PATH = os.path.dirname(__file__)

NB Loading this package does *not* install the `MaxMind database <http://dev.maxmind.com/geoip/geoip2/geolite2/>`_
. That is
your responsibility. The Country database is 2.7MB, and could be added
to most project comfortably, but it is updated regularly, and keeping that
up-to-date is out of scope for this project.

Usage
=====

Once the middleware is configured, you will be able to access Country level
information on the request object:

.. code:: python

    >>> request.country
    {
        'ip_address': '1.2.3.4',
        'country_code': 'GB',
        'country_name': 'United Kingdom'
    }

Tests
=====

The project tests are run through ``tox``.
