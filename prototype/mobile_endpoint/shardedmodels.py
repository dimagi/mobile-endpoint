from collections import defaultdict
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import exists, Column, SmallInteger, Text, Boolean, DateTime, \
    Integer, create_engine, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session, object_session
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


