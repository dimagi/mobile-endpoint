from flask import Blueprint, request

from mobile_endpoint.case.case_processing import process_cases_in_form
from mobile_endpoint.dao import SQLDao
from mobile_endpoint.extensions import requires_auth
from mobile_endpoint.form.form_processing import create_xform, get_instance_and_attachment, get_request_metadata
from mobile_endpoint.views.response import get_open_rosa_response


mod = Blueprint('receiver', __name__, url_prefix='/receiver')


@mod.route('/<domain>', methods=['POST'])
@requires_auth
def form_receiver(domain):
    instance, attachments = get_instance_and_attachment(request)
    request_meta = get_request_metadata(request)
    request_meta['domain'] = domain

    dao = SQLDao()

    xform_lock = create_xform(instance, attachments, request_meta, dao)

    with xform_lock as xform:
        cases = []
        if xform.doc_type == 'XFormInstance':
            cases = process_cases_in_form(xform, dao)

        dao.commit(xform, cases)

    return get_open_rosa_response(xform, None, None)
