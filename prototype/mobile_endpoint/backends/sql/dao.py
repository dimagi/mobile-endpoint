import json
from uuid import UUID

from sqlalchemy.orm import contains_eager, defer
from sqlalchemy.sql import exists, text
from mobile_endpoint.backends.sql.db_accessors import get_case_by_id, get_form_by_id, create_form, \
    create_or_update_case, create_or_update_case_indices, get_cases, get_open_case_ids, get_reverse_indexed_cases
from mobile_endpoint.dao import AbsctractDao, to_generic

from mobile_endpoint.exceptions import NotFound
from mobile_endpoint.models import db, Synclog, FormData, CaseData, CaseIndex, cls_for_doc_type
from mobile_endpoint.utils import get_with_lock


class SQLDao(AbsctractDao):
    def commit_atomic_submission(self, xform, case_result):
        cases = case_result.cases if case_result else []
        synclog = case_result.synclog if case_result else None

        with db.session.begin(subtransactions=True):

            create_form(xform)

            for case in cases:
                create_or_update_case(case)
                create_or_update_case_indices(case)

            if synclog:
                is_new, synclog_sql = Synclog.from_generic(synclog)
                if is_new:
                    db.session.add(synclog_sql)

            if case_result:
                case_result.commit_dirtiness_flags()

    def commit_restore(self, restore_state):
        synclog_generic = restore_state.current_sync_log
        if synclog_generic:
            _, synclog = Synclog.from_generic(synclog_generic)

            with db.session.begin():
                db.session.add(synclog)

    @to_generic
    def get_synclog(self, id):
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
        return get_form_by_id(domain, id)

    @to_generic
    def get_case(self, domain, id, lock=False):
        if lock:
            return get_with_lock('case_lock_{}'.format(id), lambda: get_case_by_id(domain, id))
        else:
            return None, get_case_by_id(domain, id)

    def case_exists(self, id):
        return CaseData.query.session.query(exists().where(CaseData.id == id)).scalar()

    @to_generic
    def get_cases(self, domain, case_ids, ordered=False):
        cases = get_cases(domain, case_ids)
        if ordered:
            # SQL won't return the rows in any particular order so we need to order them ourselves
            index_map = {UUID(id_): index for index, id_ in enumerate(case_ids)}
            ordered_cases = [None] * len(case_ids)
            for case in cases:
                ordered_cases[index_map[UUID(case.id)]] = case

            cases = ordered_cases

        return cases

    @to_generic
    def get_reverse_indexed_cases(self, domain, case_ids):
        return get_reverse_indexed_cases(domain, case_ids)

    def get_open_case_ids(self, domain, owner_id):
        return get_open_case_ids(domain, owner_id)

    def get_case_ids_modified_with_owner_since(self, domain, owner_id, reference_date):
        return [row[0] for row in CaseData.query.with_entities(CaseData.id).filter(
            CaseData.domain == domain,
            CaseData.owner_id == owner_id,
            CaseData.server_modified_on > reference_date
        )]

    def get_indexed_case_ids(self, domain, case_ids):
        return [row[0] for row in CaseIndex.query.with_entities(CaseIndex.referenced_id).filter(
            CaseIndex.domain == domain,
            CaseIndex.case_id.in_(case_ids),
        )]

    def get_last_modified_dates(self, domain, case_ids):
        """
        Given a list of case IDs, return a dict where the ids are keys and the
        values are the last server modified date of that case.
        """
        return dict(
            CaseData.query.with_entities(CaseData.id, CaseData.server_modified_on).filter(
                CaseData.domain == domain,
                CaseData.id.in_(case_ids)
            )
        )



