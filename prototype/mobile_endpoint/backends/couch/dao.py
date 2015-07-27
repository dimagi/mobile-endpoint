from couchdbkit import ResourceNotFound
from mobile_endpoint.backends.couch.models import CouchForm
from mobile_endpoint.dao import AbsctractDao, to_generic


class CouchDao(AbsctractDao):

    def commit_atomic_submission(self, xform, cases):
        is_new, form = CouchForm.from_generic(xform)
        form.save()

    def commit_restore(self, restore_state):
        pass

    def get_synclog(self, id):
        pass

    @to_generic
    def get_form(self, id):
        try:
            return CouchForm.get(id)
        except ResourceNotFound:
            return None

    def get_case(self, id, lock=False):
        pass

    def case_exists(self, id):
        pass

    def get_cases(self, case_ids, ordered=True):
        pass

    def get_reverse_indexed_cases(self, domain, case_ids):
        pass

    def get_open_case_ids(self, domain, owner_id):
        pass

    def get_case_ids_modified_with_owner_since(self, domain, owner_id, reference_date):
        pass

    def get_indexed_case_ids(self, domain, case_ids):
        pass

    def get_last_modified_dates(self, domain, case_ids):
        pass
