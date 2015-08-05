from flask import request
from mobile_endpoint.backends.couch.dao import CouchDao
from mobile_endpoint.backends.manager import get_dao
from mobile_endpoint.backends.sql.dao import SQLDao

from mobile_endpoint.case.case_processing import process_cases_in_form

from mobile_endpoint.extensions import requires_auth
from mobile_endpoint.form.form_processing import create_xform, get_instance_and_attachments, get_request_metadata
from mobile_endpoint.views import ota_mod
from mobile_endpoint.views.response import get_open_rosa_response


@ota_mod.route('/receiver/<domain>', methods=['POST'])
@requires_auth
def form_receiver(domain):
    return _receiver(domain, backend='sql')


@ota_mod.route('/couch-receiver/<domain>', methods=['POST'])
@requires_auth
def couch_receiver(domain):
    return _receiver(domain, backend='couch')

@ota_mod.route('/mongo-receiver/<domain>', methods=['POST'])
@requires_auth
def mongo_receiver(domain):
    return _receiver(domain, backend='mongo')


def _receiver(domain, backend):
    dao = get_dao(backend)
    instance, attachments = get_instance_and_attachments(request)
    request_meta = get_request_metadata(request)
    request_meta['domain'] = domain

    xform_lock = create_xform(instance, attachments, request_meta, dao)

    with xform_lock as xform:
        case_result = None
        if xform.doc_type == 'XFormInstance':
            case_result = process_cases_in_form(xform, dao)

        dao.commit_atomic_submission(xform, case_result)
        # This doesn't do anything with dirtyness flags. Should it?

    return get_open_rosa_response(xform, None, None)
