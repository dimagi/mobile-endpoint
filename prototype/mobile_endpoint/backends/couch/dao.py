from collections import defaultdict
from couchdbkit import ResourceNotFound
from mobile_endpoint.backends.couch.models import CouchForm, CouchCase, \
    CouchSynclog
from mobile_endpoint.dao import AbsctractDao, to_generic
from mobile_endpoint.exceptions import NotFound
from mobile_endpoint.utils import get_with_lock, json_format_datetime


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

        synclog = case_result.synclog if case_result else None
        if synclog:
            _, log = CouchSynclog.from_generic(synclog)
            docs_by_db[CouchSynclog.get_db()].append(log.to_json())

        for db, docs in docs_by_db.items():
            db.save_docs(docs)

        if case_result:
            # TODO: Do I need to do anything special for dirtiness flags with couch?
            case_result.commit_dirtiness_flags()

    def commit_restore(self, restore_state):
        synclog_generic = restore_state.current_sync_log
        if synclog_generic:
            _, synclog = CouchSynclog.from_generic(synclog_generic)
            synclog.save()

    @to_generic
    def get_synclog(self, id):
        try:
            return CouchSynclog.get(id)
        except ResourceNotFound:
            raise NotFound()

    def save_synclog(self, generic):
        _, synclog = CouchSynclog.from_generic(generic)
        synclog.save()

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

    @to_generic
    def get_reverse_indexed_cases(self, domain, case_ids):
        """
        Given a base list of case ids, gets all cases that reference the given cases (child cases)
        """
        keys = [[domain, case_id, 'reverse_index'] for case_id in case_ids]
        return CouchCase.view(
            'cases/related',
            keys=keys,
            reduce=False,
            include_docs=True,
        )

    def get_open_case_ids(self, domain, owner_id):
        # TODO: Not positive that this works properly yet.
        return [row['id'] for row in CouchCase.get_db().view(
            'cases/by_owner',
            key=[owner_id, False],
            reduce=False,
            include_docs=False
        )]

    def get_case_ids_modified_with_owner_since(self, domain, owner_id, reference_date):
        """
        Gets all cases with a specified owner ID that have been modified
        since a particular reference_date (using the server's timestamp)
        """
        return [
            row['id'] for row in CouchCase.get_db().view(
                'cases/by_owner_server_modified_on',
                startkey=[domain, owner_id, json_format_datetime(reference_date)],
                endkey=[domain, owner_id, {}],
                include_docs=False,
                reduce=False
            )
        ]

    def get_indexed_case_ids(self, domain, case_ids):
        """
        Given a base list of case ids, gets all ids of cases they reference (parent cases)
        """
        keys = [[domain, case_id, 'index'] for case_id in case_ids]
        return [r['value']['referenced_id'] for r in CouchCase.get_db().view(
            'cases/related',
            keys=keys,
            reduce=False,
        )]

    def get_last_modified_dates(self, domain, case_ids):
        """
        Given a list of case IDs, return a dict where the ids are keys and the
        values are the last server modified date of that case.
        """
        keys = [[domain, case_id] for case_id in case_ids]
        return dict([
            (row['id'], iso_string_to_datetime(row['value']))
            for row in CouchCase.get_db().view(
                'cases_by_server_date/by_server_modified_on',
                keys=keys,
                include_docs=False,
                reduce=False
            )
        ])
