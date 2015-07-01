from uuid import uuid4
from flask import Blueprint, jsonify, request
from mobile_endpoint.case_processing import process_cases_in_form
from mobile_endpoint.dao import SQLDao
from mobile_endpoint.extensions import requires_auth
from mobile_endpoint.form_processing import create_xform
from mobile_endpoint.utils import get_instance_and_attachment, get_request_metadata

mod = Blueprint('receiver', __name__, url_prefix='/receiver')


class Receiver(object):
    def __init__(self, dao):
        self.dao = dao

    def process_xform(self, instance, attachments, request_meta):
        xform = create_xform(instance, attachments, request_meta, self.dao)
        cases = process_cases_in_form(xform, self.dao)
        self.update_synclog(xform, cases)

        self.dao.commit()

    def update_synclog(self, xform, cases):
        pass

    def get_response(self):
        return jsonify({'tasks': [{'a': 1}]})


@mod.route('/')
@requires_auth
def index():
    instance, attachments = get_instance_and_attachment(request)
    request_meta = get_request_metadata(request)

    dao = SQLDao()

    receiver = Receiver(dao)
    receiver.process_xform(instance, attachments, request_meta)

    return receiver.get_response()
