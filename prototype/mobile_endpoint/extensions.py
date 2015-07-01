from functools import wraps
from flask.ext.redis import FlaskRedis
from flask import request, Response

redis_store = FlaskRedis()


def check_auth(auth):
    if auth.type == 'basic':
        return auth.username == 'admin' and auth.password == 'secret'


def authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(
        'Could not verify your access level for that URL.\n'
        'You have to login with proper credentials', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'})


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth):
            return authenticate()
        return f(*args, **kwargs)
    return decorated
