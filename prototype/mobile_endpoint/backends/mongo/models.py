from mobile_endpoint.form.models import XFormInstance
from mobile_endpoint.models import ToFromGeneric


class Document(object):
    _collection_name = None

    @classmethod
    def get_collection(cls):
        pass

    @classmethod
    def get(cls, id):
        """Return the document (dictionary) with the given id."""
        pass


class MongoForm(Document, ToFromGeneric):
    _collection_name = "forms"

    @classmethod
    def from_generic(cls, generic, **kwargs):
        if hasattr(generic, '_self'):
            self = generic._self
            new = False
        else:
            self = cls()
            self._id = generic.id
            new = True

        self.domain = generic.domain
        self.received_on = generic.received_on
        self.user_id = generic.metadata.userID
        self.md5 = str(generic._md5)
        self.synclog_id = generic.last_sync_token
        return new, self

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

    def to_dict(self):
        return {
            'domain': self.domain,
            'received_on': self.received_on,
            'user_id': self.user_id,  # TODO: Should this be an ObjectID object?
            'md5': self.md5,
            'synclog_id': self.synclog_id,
            '_id': self._id,
        }


class MongoCase(Document, ToFromGeneric):
    _collection_name = "cases"
