from collections import defaultdict
from mongoengine import DoesNotExist, NotUniqueError
from mobile_endpoint.dao import AbsctractDao, to_generic
from mobile_endpoint.backends.mongo.models import MongoForm, MongoCase
from couchdbkit import ResourceNotFound
from mobile_endpoint.utils import get_with_lock


class MongoDao(AbsctractDao):

    def commit_atomic_submission(self, xform, case_result):

        docs_by_collection = defaultdict(list)

        # form
        _, form = MongoForm.from_generic(xform)
        form.save()

        # cases
        cases = case_result.cases if case_result else []
        cases = [MongoCase.from_generic(case)[1] for case in cases]
        if cases:
            # TODO: Needs to be an upsert?
            MongoCase.objects.insert(cases)

        # todo sync logs
        # synclog = case_result.synclog if case_result else None


    @to_generic
    def get_form(self, id):
        try:
            return MongoForm.objects.get(id=id)
        except DoesNotExist:
            return None


    @to_generic
    def get_case(self, id, lock=False):
        def _get_case(id):
            try:
                return MongoCase.objects.get(id=id)
            except DoesNotExist:
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
        return MongoCase.objects(id__in=case_ids).all()

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
