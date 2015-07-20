import os

_basedir = os.path.abspath(os.path.dirname(__file__))

DEBUG = False
SQLALCHEMY_ECHO = False

SECRET_KEY = 'testkey'
SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:@localhost/receiver'

REDIS_URL = "redis://localhost:6379/0"

RESTORE_DIR = 'restore_tmp'

del os
