from couchdbkit import Document
from jsonobject.properties import DateTimeProperty, StringProperty, ListProperty, BooleanProperty, \
    DictProperty
from mobile_endpoint.case.models import CommCareCase
from mobile_endpoint.form.models import XFormInstance
from mobile_endpoint.models import ToFromGeneric
from mobile_endpoint.synclog.checksum import Checksum
from mobile_endpoint.synclog.models import SimplifiedSyncLog, IndexTree


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


class CouchSynclog(Document, ToFromGeneric):
    # TODO: This is basically the same as Synclog. Reuse code.

    date = DateTimeProperty()
    domain = StringProperty()
    user_id = StringProperty()
    previous_log_id = StringProperty()
    hash = StringProperty()
    owner_ids_on_phone = ListProperty(StringProperty)
    case_ids_on_phone = ListProperty(StringProperty)
    dependent_case_ids_on_phone = ListProperty(StringProperty)
    index_tree = DictProperty()

    @staticmethod
    def get_app_name():
        return 'synclogs'

    @property
    def checksum(self):
        return Checksum(initial_checksum=self.hash)

    def to_generic(self):
        synclog = SimplifiedSyncLog(
            id=self._id,
            date=self.date,
            domain=self.domain,
            user_id=self.user_id,
            previous_log_id=self.previous_log_id,
            owner_ids_on_phone=set(self.owner_ids_on_phone),
            case_ids_on_phone=set(self.case_ids_on_phone),
            dependent_case_ids_on_phone=set(self.dependent_case_ids_on_phone),
            index_tree=IndexTree(indices=self.index_tree or {})
        )
        synclog._hash = self.hash
        synclog._self = self
        return synclog

    @classmethod
    def from_generic(cls, generic, **kwargs):
        if hasattr(generic, '_self'):
            self = generic._self
            new = False
        else:
            self = cls(_id=generic.id)
            new = True

        for att in ['date', 'domain', 'user_id', 'previous_log_id', 'owner_ids_on_phone', 'case_ids_on_phone', 'dependent_case_ids_on_phone']:
            new_att = getattr(generic, att)
            # TODO: This is a hack and I hate it
            if isinstance(new_att, set):
                new_att = list(new_att)
            setattr(self, att, new_att)

        self.index_tree = generic.index_tree.indices
        self.hash = generic.get_state_hash().hash

        return new, self

