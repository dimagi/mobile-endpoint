import os

_basedir = os.path.abspath(os.path.dirname(__file__))

DEBUG = False
SQLALCHEMY_ECHO = False

SECRET_KEY = 'testkey'
SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:@localhost/receiver'
SHARDED_DATABASE_URIS = {
    'db01': 'postgresql://postgres@localhost:5432/mobile_endpoint_01',
    'db02': 'postgresql://postgres@localhost:5432/mobile_endpoint_02',
}

REDIS_URL = "redis://localhost:6379/0"

RESTORE_DIR = 'restore_tmp'

# couch settings
COUCH_URI = 'http://localhost:5984'
COUCH_DBS = {
    'forms': 'mobile_endpoint_forms',
    'cases': 'mobile_endpoint_cases',
    'synclogs': 'mobile_endpoint_synclogs',
}
# mongo settings
MONGO_URI = 'mongodb://localhost/mobile_endpoint'

del os
