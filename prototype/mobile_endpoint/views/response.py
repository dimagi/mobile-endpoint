from __future__ import absolute_import
from xml.etree import ElementTree
from flask.helpers import make_response

RESPONSE_XMLNS = 'http://openrosa.org/http/response'


class ResponseNature(object):
    """
    A const holding class for different response natures
    """
    # not super decoupled having stuff related to submissions and user reg
    # here, but nice for this all to be in one place
    SUBMIT_SUCCESS = 'submit_success'
    SUBMIT_ERROR = 'submit_error'

    # users app
    SUBMIT_USER_REGISTERED = 'submit_user_registered'
    SUBMIT_USER_UPDATED = 'submit_user_updated'

    OTA_RESTORE_SUCCESS = 'ota_restore_success'
    OTA_RESTORE_ERROR = 'ota_restore_error'


def get_response_element(message, nature=''):
    return OpenRosaResponse(message, nature, status=None).etree()


def get_simple_response_xml(message, nature=''):
    return OpenRosaResponse(message, nature, status=None).xml()


class OpenRosaResponse(object):
    """
    Response template according to
    https://bitbucket.org/javarosa/javarosa/wiki/OpenRosaRequest

    """
    def __init__(self, message, nature, status):
        self.message = message
        self.nature = nature
        self.status = status

    def etree(self):
        elem = ElementTree.Element('OpenRosaResponse')
        elem.attrib = {'xmlns': RESPONSE_XMLNS}
        msg_elem = ElementTree.Element('message')
        if self.nature:
            msg_elem.attrib = {'nature': self.nature}
        msg_elem.text = unicode(self.message)
        elem.append(msg_elem)
        return elem

    def xml(self):
        return ElementTree.tostring(self.etree(), encoding='utf-8')

    def response(self):
        return make_response(self.xml(), self.status)


OPEN_ROSA_SUCCESS_RESPONSE = OpenRosaResponse(
    message="Thanks for submitting!",
    nature=ResponseNature.SUBMIT_SUCCESS,
    status=201
)


def get_open_rosa_response(instance, responses, errors):
    if instance.doc_type == "XFormInstance":
        response = get_success_response(instance, responses, errors)
    else:
        response = get_failure_response(instance)

    # this hack is required for ODK
    # response["Location"] = self.location

    # this is a magic thing that we add
    response.headers['X-CommCareHQ-FormID'] = instance.id
    return response


def get_success_response(doc, responses, errors):

    if errors:
        response = OpenRosaResponse(
            message=doc.problem,
            nature=ResponseNature.SUBMIT_ERROR,
            status=201,
        ).response()
    elif responses:
        # use the response with the highest priority if we got any
        responses.sort()
        response = make_response(responses[-1].response, 201)
    else:
        # default to something generic
        response = OPEN_ROSA_SUCCESS_RESPONSE.response()
    return response


def get_failure_response(doc):
    return OpenRosaResponse(
        message=doc.problem,
        nature=ResponseNature.SUBMIT_ERROR,
        status=201,
    ).response()
