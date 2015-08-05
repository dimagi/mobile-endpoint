from uuid import UUID
from mongoengine import DoesNotExist
from mobile_endpoint.dao import AbsctractDao, to_generic
from mobile_endpoint.backends.mongo.models import MongoForm, MongoCase, \
    MongoSynclog
from mobile_endpoint.exceptions import NotFound
from mobile_endpoint.utils import get_with_lock


class MongoDao(AbsctractDao):

    def commit_atomic_submission(self, xform, case_result):
        # Ideally, the forms, cases, and synclogs would be saved all-or-nothing

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

        if case_result:
            case_result.commit_dirtiness_flags()


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
        # This method isn't ever used by the receiver
        return MongoCase.objects(id=UUID(id)).limit(1) is not None

    @to_generic
    def get_cases(self, case_ids, ordered=False):
        # Assumes case_ids are strings.
        cases = MongoCase.objects(id__in=case_ids)

        if ordered:
            # Mongo won't return the rows in any particular order so we need to order them ourselves
            index_map = {UUID(id_): index for index, id_ in enumerate(case_ids)}
            ordered_cases = [None] * len(case_ids)
            for case in cases:
                ordered_cases[index_map[case.id]] = case
            cases = ordered_cases

        for c in cases:
            yield c


    @to_generic
    def get_reverse_indexed_cases(self, domain, case_ids):
        """
        Given a base list of case ids, gets all cases that reference the given cases (child cases)
        """
        cases = MongoCase.objects(domain=domain, indices__referenced_id__in=case_ids)
        for c in cases:
            yield c

    def get_open_case_ids(self, domain, owner_id):
        assert isinstance(owner_id, basestring)
        return [
            unicode(c.id) for c in
            MongoCase.objects(domain=domain, owner_id=UUID(owner_id), closed=False).only('id')
        ]

    def get_case_ids_modified_with_owner_since(self, domain, owner_id, reference_date):
        return [
            unicode(c.id) for c in
            MongoCase.objects(
                domain=domain,
                owner_id=UUID(owner_id),
                server_modified_on__gt=reference_date
            ).only('id')
        ]

    def get_indexed_case_ids(self, domain, case_ids):
        """
        Given a base list of case ids, gets all ids of cases they reference (parent cases)
        """
        # NOTE: This seems to work even though case_ids are strings, which surprises me...
        cases = MongoCase.objects(id__in=case_ids).only('indices__referenced_id')
        parent_ids = set()
        for c in cases:
            parent_ids |= set(i.referenced_id for i in c.indices)
        return list(parent_ids)

    def get_last_modified_dates(self, domain, case_ids):
        """
        Given a list of case IDs, return a dict where the keys are the case ids
        and the values are the last server modified date of that case.
        """
        objs = MongoCase.objects(id__in=case_ids).only('id', 'server_modified_on')
        return {unicode(o.id): o.server_modified_on for o in objs}

    def commit_restore(self, restore_state):
        synclog_generic = restore_state.current_sync_log
        if synclog_generic:
            _, synclog = MongoSynclog.from_generic(synclog_generic)
            synclog.save()

    @to_generic
    def get_synclog(self, id):
        synclog = MongoSynclog.objects.get(id=id)
        if not synclog:
            raise NotFound()
        return synclog

    def save_synclog(self, generic):
        _, synclog = MongoSynclog.from_generic(generic)
        synclog.save()
