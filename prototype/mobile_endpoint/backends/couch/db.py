from couchdbkit import Database
from flask import current_app
from mobile_endpoint.backends.couch.models import CouchForm


def create_db(db_name):
    """
    Create couch database by name.
    """
    return get_db(db_name, create=True)


def get_db(db_name, create=False):
    """
    Get the couch database by name. Assumes all databases share the same cluster.
    """
    return Database('{}/{}'.format(current_app.config.get('COUCH_URI'), db_name), create=create)


def delete_db(db_name):
    get_db(db_name).server.delete_db(db_name)


def init_dbs():
    for cls in [CouchForm]:
        db_name = current_app.config.get('COUCH_DBS')[cls.get_app_name()]
        db = create_db(db_name)
        cls.set_db(db)
