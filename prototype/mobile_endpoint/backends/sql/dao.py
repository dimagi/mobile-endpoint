from uuid import UUID

from sqlalchemy.orm import contains_eager, defer
from mobile_endpoint.dao import AbsctractDao, to_generic

from mobile_endpoint.exceptions import NotFound
from mobile_endpoint.models import db, Synclog, FormData, CaseData, CaseIndex, cls_for_doc_type
from mobile_endpoint.utils import get_with_lock


class SQLDao(AbsctractDao):
    def commit_atomic_submission(self, xform, case_result):
        cases = case_result.cases if case_result else []
        synclog = case_result.synclog if case_result else None

        with db.session.begin(subtransactions=True):

            def get_indices():
                for case in cases:
                    for index in case.indices:
                        yield CaseIndex.from_generic(index, case.domain, case.id)

            new_form, xform_sql = cls_for_doc_type(xform.doc_type).from_generic(xform)
            case_docs = map(lambda doc: CaseData.from_generic(doc, xform_sql), cases)

            combined = [(new_form, xform_sql)] + case_docs + list(get_indices())
            if synclog:
                combined.append(Synclog.from_generic(synclog))

            for is_new, doc in combined:
                if is_new:
                    db.session.add(doc)

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
    def get_form(self, id):
        return FormData.query.get(id)

    @to_generic
    def get_case(self, id, lock=False):
        if lock:
            return get_with_lock('case_lock_{}'.format(id), lambda: CaseData.query.get(id))
        else:
            None, CaseData.query.get(id)

    def case_exists(self, id):
        return CaseData.query.filter_by(id=id).exists()

    @to_generic
    def get_cases(self, case_ids, ordered=False):
        # TODO: Should this function really be changing the default value of ordered (GenericDao has ordered=True)?
        cases = CaseData.query.filter(CaseData.id.in_(case_ids)).all()
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
        return CaseData.query.join('indices')\
            .filter(CaseIndex.domain == domain, CaseIndex.referenced_id.in_(case_ids))\
            .options(
                contains_eager('indices'),
                defer(CaseData.case_json)
        ).all()

    def get_open_case_ids(self, domain, owner_id):
        return [row[0] for row in CaseData.query.with_entities(CaseData.id).filter(
            CaseData.domain == domain,
            CaseData.owner_id == owner_id,
            CaseData.closed == False
        )]

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



