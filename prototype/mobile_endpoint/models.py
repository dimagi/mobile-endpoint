from flask.ext.migrate import Migrate
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from mobile_endpoint.case.models import CommCareCase, CommCareCaseIndex

from mobile_endpoint.form.models import doc_types


db = SQLAlchemy()

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


class FormData(db.Model, ToFromGeneric):
    __tablename__ = 'form_data'
    id = db.Column(UUID(), primary_key=True)
    domain = db.Column(db.Text(), nullable=False, index=True)
    received_on = db.Column(db.DateTime(), nullable=False)
    user_id = db.Column(UUID(), nullable=False)
    md5 = db.Column(db.BINARY(), nullable=False)
    form_json = db.Column(JSONB(), nullable=False)

    def to_generic(self):
        type_ = doc_types().get(self.type)
        generic = type_.wrap(self.form_json)
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
        self.md5 = generic.md5
        self.form_json = generic.to_json()
        return new, self

    def __repr__(self):
        return (
            "FormData("
                "id='{f.id}', "
                "domain='{f.domain}', "
                "received_on='{f.received_on}', "
                "user_id='{f.user_id}', "
                "type='{f.type}')"
        ).format(f=self)


class CaseData(db.Model, ToFromGeneric):
    __tablename__ = 'case_data'
    id = db.Column(UUID(), primary_key=True)
    domain = db.Column(db.Text(), nullable=False)
    closed = db.Column(db.Boolean(), default=False, nullable=False)
    owner_id = db.Column(UUID(), nullable=False)
    server_modified_on = db.Column(db.DateTime(), nullable=False)
    case_json = db.Column(JSONB(), nullable=False)

    forms = db.relationship("FormData", secondary=case_form_link, backref="cases")

    def to_generic(self):
        if self.case_json:
            generic = CommCareCase.wrap(self.case_json)
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
    def from_generic(cls, generic, **kwargs):
        if hasattr(generic, '_self'):
            self = generic._self
            new = False
        else:
            self = cls(id=generic.id)
            new = True

        json = generic.to_json()
        self.domain = json.pop('domain')
        self.server_modified_on = json.pop('server_modified_on')
        self.owner_id = json.pop('owner_id')
        self.closed = json.pop('closed')
        json.pop('indices')  # drop indices since they are stored separately
        self.case_json = json
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

db.Index('ix_case_data_domain_owner', CaseData.domain, CaseData.owner_id)
db.Index('ix_case_data_domain_closed_modified', CaseData.domain, CaseData.closed, CaseData.server_modified_on)


class CaseIndex(db.Model, ToFromGeneric):
    __tablename__ = 'case_index'
    case_id = db.Column(UUID(), db.ForeignKey('case_data.id'), primary_key=True)
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
    def from_generic(cls, generic, case_id=None):
        if hasattr(generic, '_self'):
            self = generic._self
            new = False
        else:
            self = cls()
            new = True

        self.identifier = generic.identifier
        self.referenced_type = generic.referenced_type
        self.referenced_id = generic.referenced_id
        if case_id:
            self.case_id = case_id

        return new, self

    def __repr__(self):
        return (
            "CaseIndex("
                "case_id='{case_id}', "
                "identifier='{identifier}', "
                "referenced_type='{ref_type}', "
                "referenced_id='{ref_id}')").format(
            case_id=self.case_id,
            identifier=self.identifier,
            ref_type=self.referenced_type,
            ref_id=self.referenced_id)

db.Index('ix_case_index_referenced_id', CaseIndex.referenced_id)

class Synclog(db.Model):
    __tablename__ = 'synclog'
    id = db.Column(UUID(), primary_key=True)
    user_id = db.Column(UUID(), nullable=False)
    previous_log_id = db.Column(UUID())
    hash = db.Column(db.Text(), nullable=False)
    owner_ids_on_phone = db.Column(ARRAY(UUID))


class SynclogCases(db.Model):
    __tablename__ = 'synclog_cases'
    synclog_id = db.Column(UUID(), db.ForeignKey('synclog.id'), primary_key=True)
    case_id = db.Column(UUID(), nullable=False)
    is_dependent = db.Column(db.Boolean(), default=False)

    synclog = db.relationship('Synclog', foreign_keys=[synclog_id], backref='cases')
