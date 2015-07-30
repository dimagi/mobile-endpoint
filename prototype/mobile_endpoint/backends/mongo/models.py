import datetime
from uuid import UUID
from flask import current_app
from mongoengine import *
from mobile_endpoint.case.models import CommCareCase
from mobile_endpoint.form.models import XFormInstance
from mobile_endpoint.models import ToFromGeneric

#connect(host=current_app.config.get('MONGO_URI'))
connect(host="mongodb://localhost/mobile_endpoint_test")


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


class MongoCase(DynamicDocument, ToFromGeneric):
    meta = {'collection': 'cases'}
    id = UUIDField(primary_key=True)
    domain = StringField()
    closed = BooleanField(default=False)
    owner_id = UUIDField()
    server_modified_on = DateTimeField()
    version = IntField()

    def to_generic(self):
        dict = self.to_mongo().to_dict()
        # TODO: This is such a hack...
        for key, value in dict.items():
            if isinstance(value, datetime.datetime):
                dict[key] = value.isoformat()
            if isinstance(value, UUID):
                dict[key] = str(value)
        dict['id'] = dict.pop('_id')
        return CommCareCase.wrap(dict)

    @classmethod
    def from_generic(cls, generic, xform=None, **kwargs):
        if hasattr(generic, '_self'):
            self = generic._self
            new = False
        else:
            case_json = generic.to_json()
            self = cls(**case_json)
            new = True

        return new, self
