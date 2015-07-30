from collections import defaultdict
from mobile_endpoint.dao import AbsctractDao, to_generic
from mobile_endpoint.backends.mongo.models import MongoForm, MongoCase
from couchdbkit import ResourceNotFound
from mobile_endpoint.utils import get_with_lock


class MongoDao(AbsctractDao):

    def commit_atomic_submission(self, xform, case_result):

        docs_by_collection = defaultdict(list)

        # form
        _, form = MongoForm.from_generic(xform)
        docs_by_collection[MongoForm.get_collection()].append(form.to_dict())

        # cases
        cases = case_result.cases if case_result else []
        for case in cases:
            docs_by_collection[MongoCase.get_collection()].append(MongoCase.from_generic(case)[1].to_dict())

        # todo sync logs
        # synclog = case_result.synclog if case_result else None
        for collection, docs in docs_by_collection.items():
            collection.insert_many(docs)


    @to_generic
    def get_form(self, id):
        return MongoForm.get(id)

    @to_generic
    def get_case(self, id, lock=False):
        def _get_case(id):
            try:
                return MongoCase.get(id)
            except ResourceNotFound:  # TODO: Replace with the right exception
                return None

        if lock:
            return get_with_lock('case_lock_{}'.format(id), lambda: _get_case(id))
        else:
            None, _get_case(id)

    def case_exists(self, id):
        pass
        # return MongoCase.get_db().doc_exist(id)

    @to_generic
    def get_cases(self, case_ids, ordered=True):
        pass

    def get_reverse_indexed_cases(self, domain, case_ids):
        # todo
        return []

    def get_open_case_ids(self, domain, owner_id):
        pass

    def get_case_ids_modified_with_owner_since(self, domain, owner_id, reference_date):
        pass

    def get_indexed_case_ids(self, domain, case_ids):
        pass

    def get_last_modified_dates(self, domain, case_ids):
        pass

    def commit_restore(self, restore_state):
        pass

    def get_synclog(self, id):
        pass
