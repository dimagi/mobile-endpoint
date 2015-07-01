from flask import Blueprint, render_template, jsonify

mod = Blueprint('receiver', __name__, url_prefix='/receiver')


@mod.route('/')
def index():
    return jsonify({'tasks': [{'a': 1}]})
