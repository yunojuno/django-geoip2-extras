# -*- coding: utf-8 -*-
from os import path, pardir, chdir

from setuptools import setup, find_packages

README = open(path.join(path.dirname(__file__), 'README.rst')).read()

# allow setup.py to be run from any path
chdir(path.normpath(path.join(path.abspath(__file__), pardir)))

setup(
    name="django-geoip2-extras",
    version="0.1.2",
    packages=find_packages(),
    install_requires=[
        'Django>=1.10',
        'geoip2>=2.4'
    ],
    include_package_data=True,
    description='Additional functionality using the GeoIP2 database.',
    license='MIT',
    long_description=README,
    url='https://github.com/yunojuno/django-geoip2-extras',
    author='YunoJuno',
    author_email='code@yunojuno.com',
    maintainer='YunoJuno',
    maintainer_email='code@yunojuno.com',
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 1.10',
        'Framework :: Django :: 1.11',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.6',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
)
