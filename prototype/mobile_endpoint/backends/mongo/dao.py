from uuid import UUID
from mongoengine import DoesNotExist
from mobile_endpoint.dao import AbsctractDao, to_generic
from mobile_endpoint.backends.mongo.models import MongoForm, MongoCase, \
    MongoSynclog
from mobile_endpoint.exceptions import NotFound
from mobile_endpoint.utils import get_with_lock


class MongoDao(AbsctractDao):

    def commit_atomic_submission(self, xform, case_result):
        # TODO: Save all in one bulk operation
        # TODO: Are the forms, cases, and synclogs all supposed to be all or nothing?

        # form
        _, form = MongoForm.from_generic(xform)
        form.save()

        # cases
        cases = case_result.cases if case_result else []
        if cases:
            collection = MongoCase._get_collection()
            bulkop = collection.initialize_unordered_bulk_op()
            for case in cases:
                mcase = MongoCase.from_generic(case)[1]
                mcase.validate()
                case_son = mcase.to_mongo()
                case_id = case_son.get('_id')
                bulkop.find({'_id': case_id}).upsert().replace_one(case_son)
            bulkop.execute()

        # synclog
        synclog = case_result.synclog if case_result else None
        if synclog:
            _, log = MongoSynclog.from_generic(synclog)
            log.save()


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
        assert isinstance(id, UUID)
        return MongoCase.objects(id=id).limit(1) is not None
        # TODO: Test this

    @to_generic
    def get_cases(self, case_ids, ordered=True):
        for c in MongoCase.objects(id__in=case_ids):
            yield c

    def get_reverse_indexed_cases(self, domain, case_ids):
        """
        Given a base list of case ids, gets all cases that reference the given cases (child cases)
        """
        return []

    def get_open_case_ids(self, domain, owner_id):
        pass

    def get_case_ids_modified_with_owner_since(self, domain, owner_id, reference_date):
        pass

    def get_indexed_case_ids(self, domain, case_ids):
        """
        Given a base list of case ids, gets all ids of cases they reference (parent cases)
        """
        pass

    def get_last_modified_dates(self, domain, case_ids):
        """
        Given a list of case IDs, return a dict where the keys are the case ids
        and the values are the last server modified date of that case.
        """
        pass

    def commit_restore(self, restore_state):
        pass

    @to_generic
    def get_synclog(self, id):
        synclog = MongoSynclog.objects.get(id=id)
        if not synclog:
            raise NotFound()
        return synclog

    def save_synclog(self, generic):
        _, synclog = MongoSynclog.from_generic(generic)
        synclog.save()
