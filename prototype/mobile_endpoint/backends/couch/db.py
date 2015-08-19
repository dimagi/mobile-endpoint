import os
from couchdbkit import Database, push
from flask import current_app
from mobile_endpoint.backends.couch.models import CouchForm, CouchCase, \
    CouchSynclog

APP = None

def create_db(db_name):
    """
    Create couch database by name.
    """
    return get_db(db_name, create=True)


def get_db(db_name, create=False, app=None):
    """
    Get the couch database by name. Assumes all databases share the same cluster.
    """
    _app = app or APP or current_app
    return Database('{}/{}'.format(_app.config.get('COUCH_URI'), db_name), create=create)


def delete_db(db_name):
    get_db(db_name).server.delete_db(db_name)


def get_app_db_name(app_name, app=None):
    app = app or current_app
    return app.config.get('COUCH_DBS')[app_name]


def get_app_db(app_name):
    return get_db(get_app_db_name(app_name))


def init_dbs():
    for cls in [CouchForm, CouchCase, CouchSynclog]:
        db_name = get_app_db_name(cls.get_app_name())
        db = create_db(db_name)
        cls.set_db(db)

    init_views()


def init_views():
    design_dir = os.path.join(os.path.dirname(__file__), '_designs')
    for app_name in os.listdir(design_dir):
        folder = os.path.join(design_dir, app_name)
        push(os.path.join(design_dir, app_name), get_app_db(app_name), force=True, docid='_design/{}'.format(app_name))
