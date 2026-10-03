"""Explicit isolated PostgreSQL test database, never reuse production secrets."""
import os

from .test_settings import *

DATABASES = {'default': {
    'ENGINE': 'django.db.backends.postgresql',
    'NAME': os.environ['BLOG_TEST_DB_NAME'],
    'USER': os.environ['BLOG_TEST_DB_USER'],
    'PASSWORD': os.environ['BLOG_TEST_DB_PASSWORD'],
    'HOST': os.environ.get('BLOG_TEST_DB_HOST', '127.0.0.1'),
    'PORT': os.environ.get('BLOG_TEST_DB_PORT', '5432'),
    'TEST': {'NAME': os.environ['BLOG_TEST_DB_NAME'] + '_tests'},
}}
