import os
from flask import Flask
from mobile_endpoint.views import receiver
from mobile_endpoint.models import db
from mobile_endpoint.extensions import redis_store


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object('config')
    app.config.from_object('localconfig')
    if 'APP_CONFIG_FILE' in os.environ:
        app.config.from_envvar('APP_CONFIG_FILE')

    redis_store.init_app(app)
    db.init_app(app)

    # register our blueprints
    app.register_blueprint(receiver.mod)

    return app
