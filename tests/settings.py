# -*- coding: utf-8 -*-
import os

DEBUG = True

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}

SECRET_KEY = "TOPSECRET"

GEOIP_PATH = os.path.dirname(__file__)

assert DEBUG is True, "This project is only intended to be used for testing."
