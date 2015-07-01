from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB

db = SQLAlchemy()


class FormData(db.Model):
    __tablename__ = 'form_data'
    id = db.Column(UUID(), primary_key=True)
    domain = db.Column(db.Text(), nullable=False, index=True)
    received_on = db.Column(db.DateTime(), nullable=False)
    user_id = db.Column(UUID(), nullable=False)
    form_json = db.Column(JSONB(), nullable=False)


class CaseData(db.Model):
    __tablename__ = 'case_data'
    id = db.Column(UUID(), primary_key=True)
    domain = db.Column(db.Text(), nullable=False)
    closed = db.Column(db.Boolean(), default=False, nullable=False)
    owner_id = db.Column(UUID(), nullable=False)
    server_modified_on = db.Column(db.DateTime(), nullable=False)
    case_json = db.Column(JSONB(), nullable=False)

    forms = db.relationship("FormData", secondary='case_form', backref="cases")

db.Index('ix_case_data_domain_owner', CaseData.domain, CaseData.owner_id)
db.Index('ix_case_data_domain_closed_modified', CaseData.domain, CaseData.closed, CaseData.server_modified_on)


class CaseIndex(db.Model):
    __tablename__ = 'case_index'
    case_id = db.Column(UUID(), db.ForeignKey('case_data.id'), primary_key=True)
    referenced_id = db.Column(UUID(), db.ForeignKey('case_data.id'), primary_key=True)

    case = db.relationship("CaseData", foreign_keys=[case_id], backref='indices')
    referenced_case = db.relationship("CaseData", foreign_keys=[referenced_id], backref='reverse_indices')


class CaseForm(db.Model):
    __tablename__ = 'case_form'
    case_id = db.Column(UUID(), db.ForeignKey('case_data.id'), primary_key=True)
    form_id = db.Column(UUID(), db.ForeignKey('form_data.id'), primary_key=True)


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
