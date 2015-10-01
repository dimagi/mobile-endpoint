from collections import defaultdict
from sqlalchemy.dialects.postgresql import UUID
import uuid
from sqlalchemy import exists, Column, SmallInteger, Text, Boolean, DateTime, \
    Integer, create_engine, Index, Table
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session, object_session, reconstructor
from sqlalchemy.orm.exc import NoResultFound
from mobile_endpoint.case.models import CommCareCase, CommCareCaseIndex
from mobile_endpoint.models import ToFromGeneric

Base = declarative_base()


class ShardManager(object):
    # This class is intended to be used as a singleton

    def __init__(self, app=None):
        self.engines = None
        self.sessions = None
        if app:
            self.init_app(app)

    def init_app(self, app):
        self.engines = {}
        self.sessions = {}
        for db_name, uri in app.config.get('SHARDED_DATABASE_URIS', {}).iteritems():
            engine = create_engine(uri)
            self.engines[db_name] = engine
            session_factory = sessionmaker(
                bind=engine,
                autocommit=True,
            )
            Session = scoped_session(session_factory)
            self.sessions[db_name] = Session

    @classmethod
    def _get_db(cls, shard_id):
        # Use a very simple shard to db mapping for now.
        # TODO: Get shard -> node mapping from config
        if shard_id == 1:
            return "db01"
        if shard_id == 2:
            return "db02"
        raise Exception("Invalid shard_id")

    def get_session(self, model_type, shard_id):
        """
        Return a session bound to the database where the given shard resides.
        """

        if not self.engines:
            raise Exception("ShardManager must be configured with an app")

        Session = self.sessions[self._get_db(shard_id)]
        return Session()

    def get_sessions(self, model_type, shard_ids):
        """
        Return a dictionary mapping sessions (bound to databases) to
        the shards that reside on that session.
        """

        # If the db is the same, the session is the same.
        # (this assumes each db has one table for each model type)
        db_to_shard_map = defaultdict(list)
        for shard in shard_ids:
            db = self._get_db(shard)
            db_to_shard_map[db].append(shard)

        return {self.get_session(model_type, v[0]): v for k, v in db_to_shard_map.iteritems()}


shard_manager = ShardManager()


class ShardedModelMixin(object):

    # TODO: Can I define table fields here?
    # (it would be good if shard_id, was here)


    @classmethod
    def get_shard_id(cls, domain, id):
        """
        Return the shard id where a CaseData with the given domain and id should
        reside.
        """
        return cls.get_shard_ids(domain)[0]
        # TODO: Select a shard by hashing the id

    @classmethod
    def get_shard_ids(cls, domain):
        """
        Return a list of shard ids where CaseData for the given domain should reside.
        """
        return [1, 2]
        # TODO: Get this from a conf

    @classmethod
    def get_base_query(cls, session, shard_ids):
        """
        Return a query on this class filtered for the given shard ids.
        """
        return session.query(cls).filter(cls.shard_id.in_(shard_ids))


# TODO: This chunk related to the sqlalchemy relationship between forms and cases
# case_form_link = Table('case_form', Base.metadata,
#     Column('case_id', UUID(), ForeignKey('case_data.id'), primary_key=True),
#     Column('form_id', UUID(), ForeignKey('form_data.id'), primary_key=True)
# )


# TODO: add indexes to this table!
case_form_link = Table('case_form_association', Base.metadata,
    Column('case_id', UUID),
    Column('shard_id', SmallInteger),
    Column('form_id', UUID),
)


class FormRelationship(object):
    """
    Use an instance of this class on CaseData to create a many-to-many
    relationship between Cases and Forms
    """
    # TODO: Eventually we would want some sort of generic "ShardedRelationship" class, but this should suffice for this POC

    def __init__(self, case):
        self.case = case  # The case that owns this relationship instance
        self.new_forms = []

    def append(self, form):
        """
        Add a form to the case that owns this relationship.

        The relationship is not saved to the DB until the owning case is saved.
        """
        self.new_forms.append(form)

    def __len__(self):
        return self._get_num_related_cases() + len(self.new_forms)

    def _get_num_related_cases(self):
        shard = CaseData.get_shard_id(self.case.domain, self.case.id)
        session = shard_manager.get_session(CaseData, shard)
        query = session.query(case_form_link).filter(
            case_form_link.c.shard_id == shard,
            case_form_link.c.case_id == self.case.id,
        )
        return query.count()


class CaseIndexRelationship(object):

    def append(self, case_index):
        pass

    def __iter__(self):
        return iter([])


class CaseData(Base, ShardedModelMixin, ToFromGeneric):

    __tablename__ = 'case_data'
    id = Column(UUID(), primary_key=True)
    shard_id = Column(SmallInteger, nullable=False)
    domain = Column(Text(), nullable=False)
    closed = Column(Boolean(), default=False, nullable=False)
    owner_id = Column(UUID(), nullable=False)
    server_modified_on = Column(DateTime(), nullable=False)
    version = Column(Integer(), default=0)
    case_json = Column(JSONB(), nullable=False)
    attachments = Column(JSONB())

    # TODO: Replace the functionality that this relationship provided
    # forms = db.relationship("FormData", secondary=case_form_link, backref="cases")

    def __init__(self, *args, **kwargs):
        super(CaseData, self).__init__(*args, **kwargs)
        self.init_on_load()

    @reconstructor
    def init_on_load(self):
        self._init_relationships()

    def _init_relationships(self):
        self.indices = CaseIndexRelationship()
        self.forms = FormRelationship(self)

    def save(self):
        assert self.id
        assert self.domain
        # TODO: Seems like there should be a more "automatic" way for setting this property
        self.shard_id = self.get_shard_id(self.domain, self.id)
        session = shard_manager.get_session(self.__class__, self.shard_id)
        # TODO: Not sure what the implications of subtransactions are, but putting in here for now to make code run :p
        with session.begin(subtransactions=True):
            session.add(self)

    @classmethod
    def get_case(cls, domain, id):
        shard = cls.get_shard_id(domain, id)
        session = shard_manager.get_session(cls, shard)
        query = cls.get_base_query(session, [shard])
        try:
            return query.filter(cls.id == id).one()
        except NoResultFound:
            return None

    @classmethod
    def case_exists(cls, domain, id):
        shard = cls.get_shard_id(domain, id)
        session = shard_manager.get_session(cls, shard)
        query = cls.get_base_query(session, [shard])

        # TODO: Do an exists query. (was having trouble making it work)
        try:
            query.filter(cls.id == id).one()
            return True
        except NoResultFound:
            return False

    @classmethod
    def get_cases(cls, domain, case_ids, ordered=False):

        shard_ids_by_session = defaultdict(list)
        case_ids_by_shard = defaultdict(list)

        for id in case_ids:
            shard = cls.get_shard_id(domain, id)
            session = shard_manager.get_session(cls, shard)
            shard_ids_by_session[session].append(shard)
            case_ids_by_shard[shard].append(id)

        cases = []
        for session, shards in shard_ids_by_session.iteritems():

            # Get the subset of the case ids that we expect to be found in this session
            session_case_ids = []
            for shard in shards:
                session_case_ids.extend(case_ids_by_shard[shard])

            cases.extend(
                cls.get_base_query(session, shards).filter(cls.id.in_(session_case_ids)).all()
            )

        if ordered:
            index_map = {uuid.UUID(id_): index for index, id_ in enumerate(case_ids)}
            ordered_cases = [None] * len(case_ids)
            for case in cases:
                ordered_cases[index_map[uuid.UUID(case.id)]] = case

            cases = ordered_cases

        return cases

    @classmethod
    def get_case_ids_modified_with_owner_since(cls, domain, owner_id, reference_date):
        sessions_map = shard_manager.get_sessions(cls, cls.get_shard_ids(domain))
        case_ids = []
        for session, shard_ids in sessions_map.iteritems():
            # psycogreen will make these requests happen concurrently (I think)
            case_ids.extend([
                row[0] for row in
                cls.get_base_query(session, shard_ids).with_entities(CaseData.id).filter(
                    CaseData.domain == domain,
                    CaseData.owner_id == owner_id,
                    CaseData.server_modified_on > reference_date
                )
            ])
        return case_ids

    @classmethod
    def get_open_case_ids(cls, domain, owner_id):
        open_case_ids = []
        for session, shard_ids in shard_manager.get_sessions(cls, cls.get_shard_ids(domain)).iteritems():
            query = cls.get_base_query(session, shard_ids).with_entities(cls.id).filter(
                cls.domain == domain,
                cls.owner_id == owner_id,
                cls.closed == False
            )
            open_case_ids.extend([row[0] for row in query])
        return open_case_ids

    @classmethod
    def get_last_modified_dates(cls, domain, case_ids):
        """
        Given a list of case IDs, return a dict where the ids are keys and the
        values are the last server modified date of that case.
        """

        shard_ids_by_session = defaultdict(list)
        case_ids_by_shard = defaultdict(list)

        for id in case_ids:
            shard = cls.get_shard_id(domain, id)
            session = shard_manager.get_session(cls, shard)
            shard_ids_by_session[session].append(shard)
            case_ids_by_shard[shard].append(id)

        results = []
        for session, shards in shard_ids_by_session.iteritems():

            # Get the subset of the case ids that we expect to be found in this session
            session_case_ids = []
            for shard in shards:
                case_ids.extend(case_ids_by_shard[shard])

            results.extend(
                cls.get_base_query(session, shards).with_entities(
                    cls.id, cls.server_modified_on
                ).filter(
                    cls.id.in_(session_case_ids)
                ).all()
            )

        return dict(results)

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

# TODO: Create these indexes in the migrations
Index('ix_case_data_domain_owner', CaseData.domain, CaseData.owner_id)
Index('ix_case_data_domain_closed_modified', CaseData.domain, CaseData.closed, CaseData.server_modified_on)
Index('ix_case_data_shard', CaseData.shard_id)


class CaseIndex(Base, ShardedModelMixin, ToFromGeneric):
    # NOTE! This is sharded on case_id
    __tablename__ = 'case_index'
    case_id = Column(UUID(), primary_key=True)
    shard_id = Column(SmallInteger, nullable=False)
    domain = Column(Text(), nullable=False)
    identifier = Column(Text(), primary_key=True)
    referenced_id = Column(UUID())
    referenced_type = Column(Text(), nullable=False)

    # TODO: Figure out how to replicate the relationship functionality (and if it is needed)
    #case = db.relationship("CaseData", foreign_keys=[case_id], backref=db.backref('indices'))
    #referenced_case = db.relationship("CaseData", foreign_keys=[referenced_id], backref='reverse_indices')

    def save(self):
        assert self.case_id
        assert self.domain
        self.shard_id = self.get_shard_id(self.domain, self.case_id)
        session = shard_manager.get_session(self.__class__, self.shard_id)
        with session.begin():
            session.add(self)

    @classmethod
    def get_reverse_indexed_case_ids(cls, domain, referenced_ids):
        # TODO: Confirm that "referenced_ids" is correct for the name of the arg
        case_ids = []
        shards = cls.get_shard_ids(domain)
        for session, shard_ids in shard_manager.get_sessions(cls, shards).iteritems():
            query = cls.get_base_query(session, shard_ids).filter(
                cls.domain == domain,
                cls.referenced_id.in_(referenced_ids)
            ).with_entities(cls.case_id)
            case_ids.extend([row[0] for row in query])
        return case_ids

    @classmethod
    def get_indexed_case_ids(cls, domain, case_ids):
        # TODO: this query follows a pattern that is used in other db accessing methods. Consider pulling this repeated logic into ShardedModelMixin
        # Query every db that contains a shard that contains a case_id in case_ids
        return_case_ids = []

        shard_ids_by_session = defaultdict(list)
        case_ids_by_shard = defaultdict(list)

        for id in case_ids:
            shard = cls.get_shard_id(domain, id)
            session = shard_manager.get_session(cls, shard)
            shard_ids_by_session[session].append(shard)
            case_ids_by_shard[shard].append(id)

        for session, shards in shard_ids_by_session.iteritems():
            # Get the subset of Case indexes that we expect to be found in this session
            session_case_ids = []
            for shard in shards:
                session_case_ids.extend(case_ids_by_shard[shard])

            return_case_ids.extend([
                row[0] for row in
                cls.get_base_query(session, shards).with_entities(cls.referenced_id).filter(
                    cls.case_id.in_(session_case_ids),
                    cls.domain == domain,
                )
            ])

        return return_case_ids

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

# TODO: Create these indexes in the migrations
Index('ix_case_index_referenced_id', CaseIndex.domain, CaseIndex.referenced_id)
