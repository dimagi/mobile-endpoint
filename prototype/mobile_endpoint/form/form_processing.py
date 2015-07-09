from datetime import datetime
import hashlib
from uuid import uuid4, UUID

from flask import logging
from werkzeug.exceptions import BadRequest

from mobile_endpoint.form.models import XFormInstance, doc_types, XFormDuplicate
from mobile_endpoint.utils import adjust_datetimes, get_with_lock, ReleaseOnError, LockManager
import xml2json


logger = logging.getLogger(__name__)

INVALID_ID = lambda id: BadRequest('Form submitted with an invalid ID: {}'.format(id))

FORM_PARAMETER_NAME = 'xml_submission_file'

MULTIPART_FILENAME_ERROR = BadRequest((
    'If you use multipart/form-data, please name your file %s.\n'
    'You may also do a normal (non-multipart) post '
    'with the xml submission as the request body instead.\n'
) % FORM_PARAMETER_NAME)
MULTIPART_EMPTY_PAYLOAD_ERROR = BadRequest((
    'If you use multipart/form-data, the file %s'
    'must not have an empty payload\n'
) % FORM_PARAMETER_NAME)
EMPTY_PAYLOAD_ERROR = BadRequest('Post may not have an empty body\n')


def get_request_metadata(request):
    """
    received_on
    date_header
    path
    submit_ip
    openrosa_headers
    """
    return {
        'last_sync_token': request.headers.get('last_sync_token', None)
    }


def get_instance_and_attachment(request):
    attachments = {}
    if 'multipart/form-data' in request.headers.get('Content-Type'):
        # ODK submission; of the form
        # $ curl --form 'xml_submission_file=@form.xml' $URL
        try:
            instance = request.files[FORM_PARAMETER_NAME].read().strip()
        except KeyError:
            raise MULTIPART_FILENAME_ERROR
        else:
            for key, item in request.files.items():
                if key != FORM_PARAMETER_NAME:
                    attachments[key] = item
        if not instance:
            raise MULTIPART_EMPTY_PAYLOAD_ERROR
    else:
        # j2me and touchforms; of the form
        # $ curl -H 'Content-Type: application/xml' --data '@form.xml' $URL
        instance = request.data
        if not instance:
            raise EMPTY_PAYLOAD_ERROR

    return instance, attachments


def create_xform(instance_xml, attachments, request_meta, dao):
    json_form = _get_xform_json(instance_xml)
    adjust_datetimes(json_form)

    xform = XFormInstance(
        # form has to be wrapped
        {'form': json_form},
        # other properties can be set post-wrap
        xmlns=json_form.get('@xmlns'),
        # _attachments=attachments_builder.to_json(),
        received_on=datetime.utcnow(),
        md5=hashlib.md5(instance_xml).hexdigest()
    )

    for key, value in request_meta.items():
        setattr(xform, key, value)

    id_from_xml = _extract_meta_field(json_form, ('instanceID', 'uuid'))
    form_id = id_from_xml or uuid4().hex
    xform['id'] = form_id
    xform_lock = aquire_xform_lock(xform)
    with ReleaseOnError(xform_lock.lock):
        if id_from_xml:
            try:
                UUID(form_id)
            except ValueError:
                raise INVALID_ID(form_id)
            else:
                existing_form = dao.get_form(form_id)
                if existing_form:
                    return handle_duplicate_form(xform_lock, existing_form)

    return xform_lock


def aquire_xform_lock(instance):
    return get_with_lock('xform-process-lock-{}'.format(instance['id']), lambda: instance)


def handle_duplicate_form(xform_lock, existing_form):
    new_form, lock = xform_lock
    conflict_id = new_form['id']
    if new_form['domain'] != existing_form['domain'] or existing_form['doc_type'] not in doc_types():
        # just change the ID and continue
        new_form['id'] = uuid4().hex
        return xform_lock
    else:

        if existing_form.md5 != new_form.md5:
            # handle form edit workflow
            pass
        else:
            # for now assume that the md5's are the same
            new_form['id'] = uuid4().hex
            new_form['doc_type'] = 'XFormDuplicate'
            dupe = XFormDuplicate.wrap(new_form.to_json())
            dupe['problem'] = "Form is a duplicate of another! (%s)" % conflict_id
            dupe['duplicate_id'] = conflict_id
            return LockManager(dupe, lock)


def _get_xform_json(xml_string):
    name, json_form = xml2json.xml2json(xml_string)
    json_form['#type'] = name
    return json_form


def _extract_meta_field(form, fields):
    """Takes form json (as returned by xml2json)"""
    if form.get('Meta'):
        # bhoma, 0.9 commcare
        meta = form['Meta']
    elif form.get('meta'):
        # commcare 1.0
        meta = form['meta']
    else:
        return None

    for field in fields:
        if field in meta:
            return meta[field]



def is_deprecation(xform):
    return xform.doc_type == deprecation_type()


def deprecation_type():
    return 'XFormDeprecated'


def is_override(xform):
    # it's an override if we've explicitly set the "deprecated_form_id" property on it.
    return bool(getattr(xform, 'deprecated_form_id', None))
