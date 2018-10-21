# -*- coding: utf-8 -*-
import os

DEBUG = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'django-geoip2-extras',
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    },
    'geoip2-extras': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'geoip2'
    }
}

SECRET_KEY = "django-geoip2-extras"

GEOIP_PATH = os.path.dirname(__file__)

GEOIP2_MIDDLEWARE_ENABLED = True

assert DEBUG is True, "This project is only intended to be used for testing."
