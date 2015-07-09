from __future__ import absolute_import

import datetime
import hashlib
from copy import copy

from jsonobject.api import re_date, JsonObject
from jsonobject.base import DefaultProperty
from jsonobject.properties import DateTimeProperty, StringProperty, DictProperty, BooleanProperty, ListProperty
from mobile_endpoint.form import const


def doc_types():
    """
    Mapping of doc_type attributes in CouchDB to the class that should be instantiated.
    """
    return {
        'XFormInstance': XFormInstance,
        # 'XFormArchived': XFormArchived,
        # 'XFormDeprecated': XFormDeprecated,
        'XFormDuplicate': XFormDuplicate,
        'XFormError': XFormError,
        # 'SubmissionErrorLog': SubmissionErrorLog,
    }


def doc_types_compressed():
    """
    Mapping of doc_type attributes in CouchDB to the class that should be instantiated.
    """
    return {
        0: XFormInstance,
        # 1: XFormArchived,
        # 2: XFormDeprecated,
        3: XFormDuplicate,
        4: XFormError,
        # 5: SubmissionErrorLog,
    }

def compressed_doc_type():
    return {v: k for k, v in doc_types_compressed()}


class Metadata(JsonObject):
    """
    Metadata of an xform, from a meta block structured like:

        <Meta>
            <timeStart />
            <timeEnd />
            <instanceID />
            <userID />
            <deviceID />
            <deprecatedID /> 
            <username />

            <!-- CommCare extension -->
            <appVersion />
            <location />
        </Meta>

    See spec: https://bitbucket.org/javarosa/javarosa/wiki/OpenRosaMetaDataSchema

    username is not part of the spec but included for convenience
    """
    timeStart = DateTimeProperty()
    timeEnd = DateTimeProperty()
    instanceID = StringProperty()
    userID = StringProperty()
    deviceID = StringProperty()
    deprecatedID = StringProperty()
    username = StringProperty()
    appVersion = StringProperty()
    # location = GeoPointProperty()


class XFormOperation(JsonObject):
    """
    Simple structure to represent something happening to a form.

    Currently used just by the archive workflow.
    """
    user = StringProperty()
    date = DateTimeProperty(default=datetime.datetime.utcnow)
    operation = StringProperty()  # e.g. "archived", "unarchived"


class XFormInstance(JsonObject):
    """An XForms instance."""
    doc_type = 'XFormInstance'
    domain = StringProperty()
    app_id = StringProperty()
    xmlns = StringProperty()
    form = DictProperty()
    received_on = DateTimeProperty()
    # Used to tag forms that were forcefully submitted
    # without a touchforms session completing normally
    partial_submission = BooleanProperty(default=False)
    history = ListProperty(XFormOperation)
    auth_context = DictProperty()
    submit_ip = StringProperty()
    path = StringProperty()
    openrosa_headers = DictProperty()
    last_sync_token = StringProperty()
    # almost always a datetime, but if it's not parseable it'll be a string
    date_header = DefaultProperty()
    build_id = StringProperty()
    export_tag = DefaultProperty(name='#export_tag')

    @property
    def type(self):
        return self.form.get(const.TAG_TYPE, "")
        
    @property
    def name(self):
        return self.form.get(const.TAG_NAME, "")

    @property
    def version(self):
        return self.form.get(const.TAG_VERSION, "")
        
    @property
    def uiversion(self):
        return self.form.get(const.TAG_UIVERSION, "")

    @property
    def metadata(self):
        def get_text(node):
            if node is None:
                return None
            if isinstance(node, dict) and '#text' in node:
                value = node['#text']
            elif isinstance(node, dict) and all(a.startswith('@') for a in node):
                return None
            else:
                value = node

            if not isinstance(value, basestring):
                value = unicode(value)
            return value

        if const.TAG_META in self.form:
            def _clean(meta_block):
                ret = copy(dict(meta_block))
                for key in ret.keys():
                    # remove attributes from the meta block
                    if key.startswith('@'):
                        del ret[key]

                # couchdbkit erroneously converts appVersion to a Decimal just because it is possible (due to it being within a "dynamic" property)
                # (see https://github.com/benoitc/couchdbkit/blob/a23343e539370cffcf8b0ce483c712911bb022c1/couchdbkit/schema/properties.py#L1038)
                ret['appVersion'] = get_text(meta_block.get('appVersion'))
                ret['location'] = get_text(meta_block.get('location'))

                # couchdbkit chokes on dates that aren't actually dates
                # so check their validity before passing them up
                if meta_block:
                    for key in ("timeStart", "timeEnd"):
                        if key in meta_block:
                            if meta_block[key]:
                                if re_date.match(meta_block[key]):
                                    # this kind of leniency is pretty bad
                                    # and making it midnight in UTC
                                    # is totally arbitrary
                                    # here for backwards compatibility
                                    meta_block[key] += 'T00:00:00.000000Z'
                                # try:
                                #     # try to parse to ensure correctness
                                #     parsed = iso_string_to_datetime(meta_block[key])
                                #     # and set back in the right format in case it was a date, not a datetime
                                #     ret[key] = json_format_datetime(parsed)
                                # except BadValueError:
                                #     # we couldn't parse it
                                #     del ret[key]
                            else:
                                # it was empty, also a failure
                                del ret[key]
                    # also clean dicts on the return value, since those are not allowed
                    for key in ret:
                        if isinstance(ret[key], dict):
                            ret[key] = ", ".join(\
                                "%s:%s" % (k, v) \
                                for k, v in ret[key].items())
                return ret
            return Metadata.wrap(_clean(self.to_json()[const.TAG_FORM][const.TAG_META]))

        return None

    def __unicode__(self):
        return "%s (%s)" % (self.type, self.xmlns)

    def xml_md5(self):
        return hashlib.md5(self.get_xml().encode('utf-8')).hexdigest()
    

class XFormError(XFormInstance):
    """
    Instances that have errors go here.
    """
    doc_type = 'XFormError'
    problem = StringProperty()
    orig_id = StringProperty()

        
class XFormDuplicate(XFormError):
    doc_type = 'XFormDuplicate'
    pass
