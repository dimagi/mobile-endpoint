from abc import ABCMeta, abstractmethod
from mobile_endpoint.models import db, Synclog


class AbsctractDao(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def commit(self):
        """
        Commit the transaction
        """
        pass

    @abstractmethod
    def get_synclog(self, id):
        pass


class SQLDao(AbsctractDao):
    def commit(self):
        db.session.commit()

    def get_synclog(self, id):
        return Synclog.query.get(id)
