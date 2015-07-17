import os
import logging
import logging.config

from flask import Flask

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

    # register our blueprints
    app.register_blueprint(ota_mod, url_prefix='/ota')

    return app
