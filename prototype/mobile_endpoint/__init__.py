import os
import logging
import logging.config

from flask import Flask
from mongoengine import connect
from mobile_endpoint.backends.couch.db import get_app_db_name, get_db
from mobile_endpoint.backends.couch.models import CouchForm, CouchCase, \
    CouchSynclog

from mobile_endpoint.views import ota_mod
from mobile_endpoint.models import db, migrate
from mobile_endpoint.extensions import redis_store


def create_app(extra_config=None):
    # logging.config.dictConfig(json.load(open('logging.json')))
    logging.basicConfig(level=logging.INFO)

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_pyfile('config.py')
    app.config.from_object('localconfig')
    if extra_config:
        app.config.from_pyfile(extra_config)
    if 'APP_CONFIG_FILE' in os.environ:
        app.config.from_envvar('APP_CONFIG_FILE')

    if not os.path.exists(app.config['RESTORE_DIR']):
            os.mkdir(app.config['RESTORE_DIR'])

    redis_store.init_app(app)
    db.init_app(app)
    migrate.init_app(app, db)

    connect(host=app.config.get('MONGO_URI'))

    for cls in [CouchForm, CouchCase, CouchSynclog]:
        db_name = get_app_db_name(cls.get_app_name(), app)
        couchdb = get_db(db_name, app=app)
        cls.set_db(couchdb)

    # register our blueprints
    app.register_blueprint(ota_mod, url_prefix='/ota')

    return app
