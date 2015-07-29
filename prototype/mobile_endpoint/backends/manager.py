from mobile_endpoint.backends.couch.dao import CouchDao
from mobile_endpoint.backends.sql.dao import SQLDao


BACKEND_SQL = 'sql'
BACKEND_COUCH = 'couch'


def get_submit_url(backend, domain):
    return {
        BACKEND_SQL: 'ota/receiver/{}'.format(domain),
        BACKEND_COUCH: 'ota/couch-receiver/{}'.format(domain),
    }[backend]


def get_dao(backend):
    return {
        BACKEND_SQL: SQLDao,
        BACKEND_COUCH: CouchDao
    }[backend]()
