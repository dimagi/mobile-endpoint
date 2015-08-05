from abc import ABCMeta, abstractmethod
import functools
import types
import redis

from mobile_endpoint.exceptions import IllegalCaseId


def to_generic(fn):
    """
    Helper decorator to convert from a DB type to a generic type by calling 'to_generic'
    on the db type. e.g. FormData to XFormInstance
    """
    def _wrap(obj):
        if hasattr(obj, 'to_generic'):
            return obj.to_generic()
        else:
            return obj

    @functools.wraps(fn)
    def _inner(*args, **kwargs):
        obj = fn(*args, **kwargs)
        if isinstance(obj, (list, tuple)):
            return [_wrap(ob) for ob in obj]
        elif isinstance(obj, types.GeneratorType):
            return (_wrap(ob) for ob in obj)
        else:
            return _wrap(obj)

    return _inner

class AbsctractDao(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def commit_atomic_submission(self, xform, case_result):
        """
        Commit the transaction
        """
        pass

    @abstractmethod
    def commit_restore(self, restore_state):
        pass

    @abstractmethod
    def get_synclog(self, id):
        pass

    @abstractmethod
    def save_synclog(self, generic):
        pass

    @abstractmethod
    def get_form(self, id):
        pass
    
    @abstractmethod
    def get_case(self, id, lock=False):
        pass

    @abstractmethod
    def case_exists(self, id):
        pass

    @abstractmethod
    def get_cases(self, case_ids, ordered=False):
        pass

    @abstractmethod
    def get_reverse_indexed_cases(self, domain, case_ids):
        """
        Given a base list of case ids, gets all cases that reference the given cases (child cases)
        """
        pass

    @abstractmethod
    def get_open_case_ids(self, domain, owner_id):
        pass

    @abstractmethod
    def get_case_ids_modified_with_owner_since(self, domain, owner_id, reference_date):
        """
        Return a list containing the id of each case in the given domain, with
        the given owner, and that was modified after the given date.
        """
        pass

    @abstractmethod
    def get_indexed_case_ids(self, domain, case_ids):
        """
        Given a base list of case ids, gets all ids of cases they reference (parent cases)
        """
        pass

    @abstractmethod
    def get_last_modified_dates(self, domain, case_ids):
        """
        Given a list of case IDs, return a dict where the ids are keys and the
        values are the last server modified date of that case.
        """
        pass


class CaseDbCache(object):
    """
    A temp object we use to keep a cache of in-memory cases around
    so we can get the latest updates even if they haven't been saved
    to the database. Also provides some type checking safety.
    """
    def __init__(self, dao, domain=None, deleted_ok=False,
                 lock=False, initial=None, xforms=None):
        self.dao = dao
        if initial:
            self.cache = {case['id']: case for case in initial}
        else:
            self.cache = {}

        self.domain = domain
        self.xforms = xforms if xforms is not None else []
        self.deleted_ok = deleted_ok
        self.lock = lock
        self.locks = []
        self._changed = set()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        for lock in self.locks:
            if lock:
                try:
                    lock.release()
                except redis.ConnectionError:
                    pass

    def validate_doc(self, doc):
        if self.domain and doc['domain'] != self.domain:
            raise IllegalCaseId("Bad case id")
        elif doc['doc_type'] == 'CommCareCase-Deleted':
            if not self.deleted_ok:
                raise IllegalCaseId("Case [%s] is deleted " % doc['id'])
        elif doc['doc_type'] != 'CommCareCase':
            raise IllegalCaseId(
                'Bad case doc type! '
                'This usually means you are using a bad value for case_id.'
                'The offending ID is {}'.format(doc['id'])
            )

    def get(self, case_id):
        if not case_id:
            raise IllegalCaseId('case_id must not be empty')
        if case_id in self.cache:
            return self.cache[case_id]

        case_doc, lock = self.dao.get_case(case_id, self.lock)
        if lock:
            self.locks.append(lock)

        if not case_doc:
            return None

        self.validate_doc(case_doc)
        self.cache[case_id] = case_doc
        return case_doc

    def set(self, case_id, case):
        self.cache[case_id] = case

    def doc_exist(self, case_id):
        return case_id in self.cache or self.dao.case_exists(case_id)

    def in_cache(self, case_id):
        return case_id in self.cache

    def populate(self, case_ids):
        """
        Populates a set of IDs in the cache in bulk.
        Use this if you know you are going to need to access these later for performance gains.
        Does NOT overwrite what is already in the cache if there is already something there.
        """
        case_ids = set(case_ids) - set(self.cache.keys())
        for case in self.dao.get_cases(case_ids):
            self.set(case['id'], case)

    def mark_changed(self, case):
        assert self.cache.get(case['id']) is case
        self._changed.add(case['id'])

    def get_changed(self):
        return [self.cache[case_id] for case_id in self._changed]

    def clear_changed(self):
        self._changed = set()

    def get_cached_forms(self):
        """
        Get any in-memory forms being processed.
        """
        return {xform.id: xform for xform in self.xforms}
