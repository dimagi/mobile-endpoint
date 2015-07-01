from flask import Blueprint, jsonify
from mobile_endpoint.extensions import requires_auth

mod = Blueprint('receiver', __name__, url_prefix='/receiver')


@mod.route('/')
@requires_auth
def index():
    return jsonify({'tasks': [{'a': 1}]})
