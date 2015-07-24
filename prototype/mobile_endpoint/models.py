from datetime import datetime
from flask.ext.migrate import Migrate
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy import event
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from sqlalchemy.orm.session import object_session
from mobile_endpoint.case.models import CommCareCase, CommCareCaseIndex

from mobile_endpoint.form.models import XFormInstance, doc_types_compressed, compressed_doc_type
from mobile_endpoint.synclog.checksum import Checksum
from mobile_endpoint.synclog.models import SimplifiedSyncLog, IndexTree

db = SQLAlchemy(session_options={'autocommit': True})

migrate = Migrate()


class ToFromGeneric(object):
    def to_generic(self):
        raise NotImplementedError()

    @classmethod
    def from_generic(cls, obj_dict, **kwargs):
        raise NotImplementedError()


case_form_link = db.Table('case_form', db.Model.metadata,
    db.Column('case_id', UUID(), db.ForeignKey('case_data.id'), primary_key=True),
    db.Column('form_id', UUID(), db.ForeignKey('form_data.id'), primary_key=True)
)


def cls_for_doc_type(doc_type):
    return FormData if doc_type == 'XFormInstance' else FormError


class FormData(db.Model, ToFromGeneric):
    __tablename__ = 'form_data'
    id = db.Column(UUID(), primary_key=True)
    domain = db.Column(db.Text(), nullable=False, index=True)
    received_on = db.Column(db.DateTime(), nullable=False)
    user_id = db.Column(UUID(), nullable=False)
    md5 = db.Column(db.LargeBinary(), nullable=False)
    synclog_id = db.Column(UUID(), db.ForeignKey('synclog.id'))
    attachments = db.Column(JSONB())

    synclog = db.relationship("Synclog", foreign_keys=[synclog_id])

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
            self = cls(id=generic.id)
            new = True

        self.domain = generic.domain
        self.received_on = generic.received_on
        self.user_id = generic.metadata.userID
        self.md5 = str(generic._md5)
        self.synclog_id = generic.last_sync_token
        return new, self

    def __repr__(self):
        return (
            "FormData("
                "id='{f.id}', "
                "domain='{f.domain}', "
                "received_on='{f.received_on}', "
                "user_id='{f.user_id}')"
        ).format(f=self)


class FormError(db.Model, ToFromGeneric):
    __tablename__ = 'form_error'
    id = db.Column(UUID(), primary_key=True)
    domain = db.Column(db.Text(), nullable=False, index=True)
    received_on = db.Column(db.DateTime(), nullable=False)
    user_id = db.Column(UUID(), nullable=False)
    md5 = db.Column(db.LargeBinary(), nullable=False)
    type = db.Column(db.Integer(), nullable=False)
    duplicate_id = db.Column(UUID(), db.ForeignKey('form_data.id'))
    attachments = db.Column(JSONB())

    def to_generic(self):
        generic = doc_types_compressed().get(self.type)()
        generic.id = self.id,
        generic.domain = self.domain,
        generic.received_on = self.received_on,
        generic.user_id = self.user_id
        generic._md5 = self.md5
        generic.duplicate_id = self.duplicate_id
        generic.last_sync_token = self.synclog_id
        generic._self = self
        return generic

    @classmethod
    def from_generic(cls, generic, **kwargs):
        if hasattr(generic, '_self'):
            self = generic._self
            new = False
        else:
            self = cls(id=generic.id)
            new = True

        self.domain = generic.domain
        self.received_on = generic.received_on
        self.user_id = generic.metadata.userID
        self.md5 = str(generic._md5)
        self.problem = generic.problem
        self.type = compressed_doc_type()[generic.doc_type]
        self.duplicate_id = getattr(generic, 'duplicate_id', None)
        return new, self

    @property
    def full_type(self):
        return doc_types_compressed().get(self.type)

    def __repr__(self):
        return (
            "FormError("
                "id='{f.id}', "
                "domain='{f.domain}', "
                "received_on='{f.received_on}', "
                "user_id='{f.user_id}', "
                "type='{f.full_type}', "
                "md5='{f.md5}', "
                "problem='{f.problem}', "
                "duplicate_id='{f.duplicate_id}', "
                ")"
        ).format(f=self)


class CaseData(db.Model, ToFromGeneric):
    __tablename__ = 'case_data'
    id = db.Column(UUID(), primary_key=True)
    domain = db.Column(db.Text(), nullable=False)
    closed = db.Column(db.Boolean(), default=False, nullable=False)
    owner_id = db.Column(UUID(), nullable=False)
    server_modified_on = db.Column(db.DateTime(), nullable=False)
    version = db.Column(db.Integer(), default=0)
    case_json = db.Column(JSONB(), nullable=False)
    attachments = db.Column(JSONB())

    forms = db.relationship("FormData", secondary=case_form_link, backref="cases")

    def to_generic(self):
        if self.case_json:
            generic = CommCareCase.wrap(self.case_json)
            generic.indices = []
        else:
            generic = CommCareCase()

        generic.id = self.id
        generic.owner_id = self.owner_id
        generic.closed = self.closed
        generic.domain = self.domain
        generic.server_modified_on = self.server_modified_on
        for index in self.indices:
            generic.indices.append(index.to_generic())
        generic._self = self
        return generic

    @classmethod
    def from_generic(cls, generic, xform=None, **kwargs):
        if hasattr(generic, '_self'):
            self = generic._self
            new = False
        else:
            self = cls(id=generic.id)
            new = True

        json = generic.to_json()
        json.pop('indices')  # drop indices since they are stored separately
        for att in ['domain', 'owner_id', 'closed', 'server_modified_on']:
            setattr(self, att, getattr(generic, att))
            json.pop(att)
        self.case_json = json

        if xform:
            self.forms.append(xform)

        return new, self

    def __repr__(self):
        return (
            "CaseData("
                "id='{c.id}', "
                "domain='{c.domain}', "
                "closed={c.closed}, "
                "owner_id='{c.owner_id}', "
                "server_modified_on='{c.server_modified_on}')"
        ).format(c=self)


@event.listens_for(CaseData, "before_update")
def update_version(mapper, connection, instance):
    if object_session(instance).is_modified(instance):
        instance.version = (instance.version or 0) + 1

db.Index('ix_case_data_domain_owner', CaseData.domain, CaseData.owner_id)
db.Index('ix_case_data_domain_closed_modified', CaseData.domain, CaseData.closed, CaseData.server_modified_on)


class CaseIndex(db.Model, ToFromGeneric):
    __tablename__ = 'case_index'
    case_id = db.Column(UUID(), db.ForeignKey('case_data.id'), primary_key=True)
    domain = db.Column(db.Text(), nullable=False)
    identifier = db.Column(db.Text(), primary_key=True)
    referenced_id = db.Column(UUID(), db.ForeignKey('case_data.id'))
    referenced_type = db.Column(db.Text(), nullable=False)

    case = db.relationship("CaseData", foreign_keys=[case_id], backref=db.backref('indices'))
    referenced_case = db.relationship("CaseData", foreign_keys=[referenced_id], backref='reverse_indices')

    def to_generic(self):
        index = CommCareCaseIndex.from_case_index_update(self)
        index._self = self
        return index

    @classmethod
    def from_generic(cls, generic, domain=None, case_id=None, **kwargs):
        if hasattr(generic, '_self'):
            self = generic._self
            new = False
        else:
            self = cls(case_id=case_id, domain=domain)
            new = True

        for att in ['identifier', 'referenced_type', 'referenced_id', 'referenced_type']:
            setattr(self, att, getattr(generic, att))

        return new, self

    def __repr__(self):
        return (
            "CaseIndex("
                "case_id='{case_id}', "
                "domain='{domain}', "
                "identifier='{identifier}', "
                "referenced_type='{ref_type}', "
                "referenced_id='{ref_id}')").format(
            case_id=self.case_id,
            domain=self.domain,
            identifier=self.identifier,
            ref_type=self.referenced_type,
            ref_id=self.referenced_id)

db.Index('ix_case_index_referenced_id', CaseIndex.domain, CaseIndex.referenced_id)


class Synclog(db.Model, ToFromGeneric):
    __tablename__ = 'synclog'
    id = db.Column(UUID(), primary_key=True)
    date = db.Column(db.DateTime(), nullable=False)
    domain = db.Column(db.Text(), nullable=False)
    user_id = db.Column(UUID(), nullable=False)
    previous_log_id = db.Column(UUID(), db.ForeignKey(id))
    hash = db.Column(db.LargeBinary(), nullable=False)
    owner_ids_on_phone = db.Column(ARRAY(UUID))
    case_ids_on_phone = db.Column(ARRAY(UUID))
    dependent_case_ids_on_phone = db.Column(ARRAY(UUID))
    index_tree = db.Column(JSONB())

    @property
    def checksum(self):
        return Checksum(initial_checksum=self.hash)

    def to_generic(self):
        synclog = SimplifiedSyncLog(
            id=self.id,
            date=self.date,
            domain=self.domain,
            user_id=self.user_id,
            previous_log_id=self.previous_log_id,
            owner_ids_on_phone=set(self.owner_ids_on_phone or []),
            case_ids_on_phone=set(self.case_ids_on_phone or []),
            dependent_case_ids_on_phone=set(self.dependent_case_ids_on_phone or []),
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
            setattr(self, att, getattr(generic, att))

        self.index_tree = generic.index_tree.indices
        self.hash = generic.get_state_hash().hash
        
        return new, self

    def __repr__(self):
        return (
            "Synclog("
                "id='{s.id}', "
                "domain='{s.domain}', "
                "date='{s.date}', "
                "user_id='{s.user_id}', "
                "previous_log_id='{s.previous_log_id}, "
                "hash='{s.hash}')").format(s=self)


class OwnershipCleanlinessFlag(db.Model):
    """
    Stores whether an owner_id is "clean" aka has a case universe only belonging
    to that ID.

    We use this field to optimize restores.
    """
    __tablename__ = 'ownership_cleanliness_flag'
    domain = db.Column(db.Text(), primary_key=True)
    owner_id = db.Column(UUID(), primary_key=True)
    is_clean = db.Column(db.Boolean(), nullable=False, default=False)
    last_checked = db.Column(db.DateTime(), nullable=False, default=datetime.utcnow())
    hint = db.Column(UUID(), db.ForeignKey('case_data.id'))

    @classmethod
    def get_or_create(cls, domain, owner_id, defaults=None):
        instance = cls.query.filter_by(domain=domain, owner_id=owner_id).first()
        if instance:
            return instance
        else:
            instance = OwnershipCleanlinessFlag(domain=domain, owner_id=owner_id)
            if defaults:
                for field, value in defaults.items():
                    setattr(instance, field, value)
            with db.session.begin(subtransactions=True):
                db.session.add(instance)
            return instance


@event.listens_for(OwnershipCleanlinessFlag, "before_update")
def gen_default(mapper, connection, instance):
    if object_session(instance).is_modified(instance, include_collections=False):
        instance.last_checked = datetime.utcnow()
