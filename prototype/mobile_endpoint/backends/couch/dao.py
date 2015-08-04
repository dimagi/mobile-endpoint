from collections import defaultdict
from couchdbkit import ResourceNotFound
from mobile_endpoint.backends.couch.models import CouchForm, CouchCase
from mobile_endpoint.dao import AbsctractDao, to_generic
from mobile_endpoint.utils import get_with_lock


class CouchDao(AbsctractDao):

    def commit_atomic_submission(self, xform, case_result):

        docs_by_db = defaultdict(list)

        # form
        is_new, form = CouchForm.from_generic(xform)
        docs_by_db[CouchForm.get_db()].append(form.to_json())

        # cases
        cases = case_result.cases if case_result else []
        for case in cases:
            docs_by_db[CouchCase.get_db()].append(CouchCase.from_generic(case)[1].to_json())

        # todo sync logs
        # synclog = case_result.synclog if case_result else None
        for db, docs in docs_by_db.items():
            db.save_docs(docs)

    def commit_restore(self, restore_state):
        pass

    def get_synclog(self, id):
        pass

    def save_synclog(self, generic):
        # TODO
        pass

    @to_generic
    def get_form(self, id):
        try:
            return CouchForm.get(id)
        except ResourceNotFound:
            return None

    @to_generic
    def get_case(self, id, lock=False):
        def _get_case(id):
            try:
                return CouchCase.get(id)
            except ResourceNotFound:
                return None

        if lock:
            return get_with_lock('case_lock_{}'.format(id), lambda: _get_case(id))
        else:
            None, _get_case(id)

    def case_exists(self, id):
        return CouchCase.get_db().doc_exist(id)

    @to_generic
    def get_cases(self, case_ids, ordered=False):
        for row in CouchCase.view('_all_docs', keys=case_ids, include_docs=True):
            yield row

    def get_reverse_indexed_cases(self, domain, case_ids):
        """
        Given a base list of case ids, gets all cases that reference the given cases (child cases)
        """
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
