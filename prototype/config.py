import os

_basedir = os.path.abspath(os.path.dirname(__file__))

DEBUG = False
SQLALCHEMY_ECHO = False

SECRET_KEY = 'testkey'
SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:@localhost/receiver'

REDIS_URL = "redis://localhost:6379/0"

COUCH_URI = 'http://localhost:5984/mobile_endpoint'

MONGO_URI = ''  # TODO: install mongo, get this uri.

del os
