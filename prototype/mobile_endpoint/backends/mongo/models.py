import datetime
from uuid import UUID
from mongoengine import *
from mobile_endpoint.case.models import CommCareCase
from mobile_endpoint.form.models import XFormInstance
from mobile_endpoint.models import ToFromGeneric
from mobile_endpoint.synclog.checksum import Checksum
from mobile_endpoint.synclog.models import SimplifiedSyncLog, IndexTree


class MongoForm(Document, ToFromGeneric):
    meta = {'collection': 'forms'}

    # TODO: Add indexes and constraints
    id = UUIDField(primary_key=True)
    domain = StringField()
    received_on = DateTimeField()
    user_id = UUIDField()
    md5 = BinaryField()  # TODO: Figure out how this field works
    synclog_id = UUIDField()

    def to_generic(self):
        generic = XFormInstance(
            id=self.id,
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
            self = cls()
            self.id = generic.id
            new = True

        self.domain = generic.domain
        self.received_on = generic.received_on
        self.user_id = generic.metadata.userID
        self.md5 = str(generic._md5)
        self.synclog_id = generic.last_sync_token

        return new, self


class MongoCaseIndex(EmbeddedDocument):
    identifier = StringField()
    referenced_type = StringField()
    referenced_id = UUIDField()

class MongoCase(DynamicDocument, ToFromGeneric):
    meta = {'collection': 'cases'}
    id = UUIDField(primary_key=True)
    domain = StringField()
    closed = BooleanField(default=False)
    owner_id = UUIDField()
    server_modified_on = DateTimeField()
    version = StringField()
    indices = ListField(EmbeddedDocumentField(MongoCaseIndex))

    def to_generic(self):
        dict = self.to_mongo().to_dict()

        # TODO: This is such a hack...
        for key, value in dict.items():
            if isinstance(value, datetime.datetime):
                dict[key] = value.isoformat()
            if isinstance(value, UUID):
                dict[key] = str(value)
        for index in dict['indices']:
            index['referenced_id'] = str(index['referenced_id'])
        dict['id'] = dict.pop('_id')

        return CommCareCase.wrap(dict)

    @classmethod
    def from_generic(cls, generic, xform=None, **kwargs):
        if hasattr(generic, '_self'):
            self = generic._self
            new = False
        else:
            case_json = generic.to_json()
            # Convert the case indexes to documents
            case_json['indices'] = [MongoCaseIndex(**i) for i in case_json['indices']]
            self = cls(**case_json)
            # Looks like fields aren't cleaned/converted to the right type
            # until document saving or validation (?). So, self.id will be a
            # string, not a UUID.
            new = True

        return new, self


class MongoSynclog(Document):
    # TODO: This is basically the same as Synclog. Reuse code.

    meta = {'collection': 'synclogs'}

    id = UUIDField(primary_key=True)
    date = DateTimeField()
    domain = StringField()
    user_id = UUIDField()
    previous_log_id = UUIDField()
    hash = BinaryField()
    owner_ids_on_phone = ListField(UUIDField())
    case_ids_on_phone = ListField(UUIDField())
    dependent_case_ids_on_phone = ListField(UUIDField())
    index_tree = DictField()

    @property
    def checksum(self):
        return Checksum(initial_checksum=self.hash)

    def to_generic(self):
        synclog = SimplifiedSyncLog(
            id=self.id and unicode(self.id),  # this converts UUIDs to strings, but preserves None
            date=self.date,
            domain=self.domain,
            user_id=self.user_id and unicode(self.user_id),
            previous_log_id=self.previous_log_id and unicode(self.previous_log_id),
            owner_ids_on_phone=set(unicode(i) for i in self.owner_ids_on_phone),
            case_ids_on_phone=set(unicode(i) for i in self.case_ids_on_phone),
            dependent_case_ids_on_phone=set(unicode(i) for i in self.dependent_case_ids_on_phone),
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
            self = cls(id=generic.id)
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
