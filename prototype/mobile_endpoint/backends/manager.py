from mobile_endpoint.backends.couch.dao import CouchDao
from mobile_endpoint.backends.sql.dao import SQLDao
from mobile_endpoint.backends.mongo.dao import MongoDao


BACKEND_SQL = 'sql'
BACKEND_COUCH = 'couch'
BACKEND_MONGO = 'mongo'


def get_submit_url(backend, domain):
    return {
        BACKEND_SQL: 'ota/receiver/{}'.format(domain),
        BACKEND_COUCH: 'ota/couch-receiver/{}'.format(domain),
        BACKEND_MONGO: 'ota/mongo-receiver/{}'.format(domain),
    }[backend]


def get_dao(backend):
    return {
        BACKEND_SQL: SQLDao,
        BACKEND_COUCH: CouchDao,
        BACKEND_MONGO: MongoDao,
    }[backend]()
