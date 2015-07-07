from flask.ext.migrate import Migrate
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB

db = SQLAlchemy()

migrate = Migrate()



case_form_link = db.Table('case_form', db.Model.metadata,
    db.Column('case_id', UUID(), db.ForeignKey('case_data.id'), primary_key=True),
    db.Column('form_id', UUID(), db.ForeignKey('form_data.id'), primary_key=True)
)
    __tablename__ = 'form_data'
    id = db.Column(UUID(), primary_key=True)
    domain = db.Column(db.Text(), nullable=False, index=True)
    received_on = db.Column(db.DateTime(), nullable=False)
    user_id = db.Column(UUID(), nullable=False)
    type = db.Column(db.Text(), default='XFormInstance')
    form_json = db.Column(JSONB(), nullable=False)


class CaseData(db.Model):
    __tablename__ = 'case_data'
    id = db.Column(UUID(), primary_key=True)
    domain = db.Column(db.Text(), nullable=False)
    closed = db.Column(db.Boolean(), default=False, nullable=False)
    owner_id = db.Column(UUID(), nullable=False)
    server_modified_on = db.Column(db.DateTime(), nullable=False)
    case_json = db.Column(JSONB(), nullable=False)

    forms = db.relationship("FormData", secondary=case_form_link, backref="cases")


db.Index('ix_case_data_domain_owner', CaseData.domain, CaseData.owner_id)
db.Index('ix_case_data_domain_closed_modified', CaseData.domain, CaseData.closed, CaseData.server_modified_on)


class CaseIndex(db.Model):
    __tablename__ = 'case_index'
    case_id = db.Column(UUID(), db.ForeignKey('case_data.id'), primary_key=True)
    identifier = db.Column(db.Text(), primary_key=True)
    referenced_id = db.Column(UUID(), db.ForeignKey('case_data.id'))
    referenced_type = db.Column(db.Text(), nullable=False)

    case = db.relationship("CaseData", foreign_keys=[case_id], backref=db.backref('indices'))
    referenced_case = db.relationship("CaseData", foreign_keys=[referenced_id], backref='reverse_indices')



db.Index('ix_unique_case_index_case_id_identifier', CaseIndex.case_id, CaseIndex.identifier, unique=True)

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
