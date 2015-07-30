from pymongo import MongoClient
from flask import current_app

def client():
    # TODO: Read a bit more about how pymongo does connection pooling
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
