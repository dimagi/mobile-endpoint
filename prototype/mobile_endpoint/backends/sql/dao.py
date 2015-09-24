from collections import defaultdict
from uuid import UUID

from sqlalchemy.orm import contains_eager, defer
from sqlalchemy.sql import exists
from mobile_endpoint.dao import AbsctractDao, to_generic

from mobile_endpoint.exceptions import NotFound
from mobile_endpoint.models import db, Synclog, FormData, cls_for_doc_type
from mobile_endpoint import shardedmodels
from mobile_endpoint.utils import get_with_lock


class SQLDao(AbsctractDao):
    def commit_atomic_submission(self, xform, case_result):
        # TODO: Pretty sure this function isn't working quite right
        cases = case_result.cases if case_result else []
        synclog = case_result.synclog if case_result else None

        def get_indices():
            for case in cases:
                for index in case.indices:
                    yield shardedmodels.CaseIndex.from_generic(index, case.domain, case.id)

        new_form, xform_sql = cls_for_doc_type(xform.doc_type).from_generic(xform)
        case_docs = map(lambda doc: shardedmodels.CaseData.from_generic(doc, xform_sql), cases)

        with db.session.begin(subtransactions=True):

            # Save the non-sharded models
            standard_db_model_instances = [(new_form, xform_sql)]
            if synclog:
                standard_db_model_instances.append(Synclog.from_generic(synclog))
            for is_new, doc in standard_db_model_instances:
                if is_new:
                    db.session.add(doc)

            if case_result:
                case_result.commit_dirtiness_flags()

        # Save the sharded models
        sharded_db_model_instances = case_docs + list(get_indices())
        for doc in sharded_db_model_instances:
            doc.save()

    def commit_restore(self, restore_state):
        synclog_generic = restore_state.current_sync_log
        if synclog_generic:
            _, synclog = Synclog.from_generic(synclog_generic)

            with db.session.begin():
                db.session.add(synclog)

    @to_generic
    def get_synclog(self, domain, id):
        synclog = Synclog.query.get(id)
        if not synclog:
            raise NotFound()

        return synclog

    def save_synclog(self, generic):
        with db.session.begin():
            _, synclog = Synclog.from_generic(generic)
            db.session.add(synclog)

    @to_generic
    def get_form(self, domain, id):
        return FormData.query.get(id)

    @to_generic
    def get_case(self, domain, id, lock=False):
        if lock:
            return get_with_lock('case_lock_{}'.format(id), lambda: shardedmodels.CaseData.get_case(domain, id))
        else:
            None, shardedmodels.CaseData.get_case(domain, id)

    def case_exists(self, domain, id):
        return shardedmodels.CaseData.case_exists(domain, id)

    @to_generic
    def get_cases(self, domain, case_ids, ordered=False):
        return shardedmodels.CaseData.get_cases(domain, case_ids, ordered)

    @to_generic
    def get_reverse_indexed_cases(self, domain, case_ids):
        # TODO: If we were clever, we would do database level joins
        case_ids = shardedmodels.CaseIndex.get_reverse_indexed_case_ids(domain, case_ids)
        cases = shardedmodels.CaseData.get_cases(domain, case_ids)
        return cases

    def get_open_case_ids(self, domain, owner_id):
        return shardedmodels.CaseData.get_open_case_ids(domain, owner_id)

    def get_case_ids_modified_with_owner_since(self, domain, owner_id, reference_date):
        return shardedmodels.CaseData.get_case_ids_modified_with_owner_since(domain, owner_id, reference_date)

    def get_indexed_case_ids(self, domain, case_ids):
        return shardedmodels.CaseIndex.get_indexed_case_ids(domain, case_ids)

    def get_last_modified_dates(self, domain, case_ids):
        """
        Given a list of case IDs, return a dict where the ids are keys and the
        values are the last server modified date of that case.
        """
        return shardedmodels.CaseData.get_last_modified_dates(domain, case_ids)


