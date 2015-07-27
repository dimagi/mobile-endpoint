from couchdbkit import Database
from flask import current_app


def create_db(db_name):
    """
    Create couch database by name.
    """
    get_db(db_name, create=True)


def get_db(db_name, create=False):
    """
    Get the couch database by name. Assumes all databases share the same cluster.
    """
    return Database('{}/{}'.format(current_app.config.get('COUCH_URI'), db_name), create=create)
