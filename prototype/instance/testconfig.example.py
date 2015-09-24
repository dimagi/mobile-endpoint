DEBUG = True
SQLALCHEMY_ECHO = False
TESTING = True

SQLALCHEMY_DATABASE_URI= 'postgresql://postgres:password@localhost/mobile_endpoint'
SHARDED_DATABASE_URIS = {
    'db01': 'postgresql://postgres:password@localhost:5432/mobile_endpoint_01',
    'db02': 'postgresql://postgres:password@localhost:5432/mobile_endpoint_02',
}

COUCH_URI = 'http://localhost:5984'

MONGO_URI = 'mongodb://localhost/mobile_endpoint_test'
