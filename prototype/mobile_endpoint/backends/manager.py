from mobile_endpoint.backends.couch.dao import CouchDao
from mobile_endpoint.backends.sql.dao import SQLDao


def get_dao(backend):
    return {
        'sql': SQLDao,
        'couch': CouchDao
    }[backend]()
