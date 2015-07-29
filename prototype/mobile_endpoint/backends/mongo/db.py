from pymongo import MongoClient
from flask import current_app
from mobile_endpoint.backends.mongo.models import MongoForm, MongoCase


def client():
    return MongoClient(current_app.config.get('MONGO_URI'))


def get_db():
    """
    Get the couch database by name. Assumes all databases share the same cluster.
    """
    # TODO: Make sure database is specified in mongo uri
    return client().get_default_database()


def delete_db():
    c = client()
    db = c.get_db()
    c.drop_database(db)


def init_dbs():
    for cls in [MongoForm, MongoCase]:
        db_name = current_app.config.get('COUCH_DBS')[cls.get_app_name()]
        db = create_db(db_name)
        cls.set_db(db)
