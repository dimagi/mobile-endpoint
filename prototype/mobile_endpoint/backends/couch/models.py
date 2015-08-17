from couchdbkit import Document
from jsonobject.properties import DateTimeProperty, StringProperty, ListProperty, BooleanProperty
from mobile_endpoint.case.models import CommCareCase
from mobile_endpoint.form.models import XFormInstance
from mobile_endpoint.models import ToFromGeneric


class CouchForm(Document, ToFromGeneric):

    domain = StringProperty()
    received_on = DateTimeProperty()
    user_id = StringProperty()
    synclog_id = StringProperty()

    @staticmethod
    def get_app_name():
        return 'forms'

    def to_generic(self):
        generic = XFormInstance(
            id=self._id,
            domain=self.domain,
            received_on=self.received_on,
            user_id=self.user_id,
            last_sync_token=self.synclog_id
        )
        generic._self = self
        generic._md5 = self.md5
        return generic

    @classmethod
    def from_generic(cls, generic, **kwargs):
        if hasattr(generic, '_self'):
            self = generic._self
            new = False
        else:
            self = cls(_id=generic.id)
            new = True

        self.domain = generic.domain
        self.received_on = generic.received_on
        self.user_id = generic.metadata.userID
        self.md5 = str(generic._md5)
        self.synclog_id = generic.last_sync_token
        return new, self


class CouchCaseIndex(Document):
    identifier = StringProperty()
    referenced_type = StringProperty()
    referenced_id = StringProperty()


class CouchCase(Document, ToFromGeneric):
    domain = StringProperty()
    closed = BooleanProperty(default=False)
    owner_id = StringProperty()
    server_modified_on = DateTimeProperty()
    version = StringProperty()
    indices = ListProperty(CouchCaseIndex)

    @staticmethod
    def get_app_name():
        return 'cases'

    def to_generic(self):
        json = self.to_json()
        json['id'] = json.pop('_id')
        return CommCareCase.wrap(json)

    @classmethod
    def from_generic(cls, generic, xform=None, **kwargs):
        if hasattr(generic, '_self'):
            self = generic._self
            new = False
        else:
            case_json = generic.to_json()
            id = case_json.pop('id')
            case_json['_id'] = id
            self = cls.wrap(case_json)
            new = True

        return new, self
