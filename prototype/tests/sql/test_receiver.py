import pytest
from mobile_endpoint.backends.manager import BACKEND_SQL
from mobile_endpoint.models import FormData, CaseData, Synclog
from mobile_endpoint.synclog.checksum import Checksum
from tests.conftest import sql
from tests.test_receiver import ReceiverTestMixin, DOMAIN


@pytest.mark.usefixtures("testapp", "client", "sqldb", "db_reset")
@sql
class TestPostgresReceiver(ReceiverTestMixin):

    def _get_backend(self):
        return BACKEND_SQL

    def _assert_form(self, form_id, user_id, synclog_id=None):
        sql_form = FormData.query.get(form_id)
        assert sql_form is not None
        assert sql_form.domain == DOMAIN
        assert sql_form.user_id == user_id
        if synclog_id:
            assert sql_form.synclog_id == synclog_id
        else:
            assert sql_form.synclog_id is None

    def _assert_case(self, case_id, owner_id, num_forms=1, closed=False, indices=None):
        sql_case = CaseData.query.get(case_id)
        assert sql_case is not None
        assert sql_case.domain == DOMAIN
        assert sql_case.closed == closed
        assert len(sql_case.forms) == num_forms
        assert sql_case.owner_id == owner_id

        if indices:
            sql_indices = {}
            for index in sql_case.indices:
                sql_indices[index.identifier] = {
                    'referenced_type': index.referenced_type,
                    'referenced_id': index.referenced_id
                }

            assert sql_indices == indices

        return sql_case

    def _assert_synclog(self, id, case_ids=None, dependent_ids=None, index_tree=None):
        synclog = Synclog.query.get(id)
        case_ids = case_ids or []
        dependent_ids = dependent_ids or []
        index_tree = index_tree or {}
        assert case_ids == synclog.case_ids_on_phone
        assert dependent_ids == synclog.dependent_case_ids_on_phone
        assert index_tree == synclog.index_tree
        assert Checksum(case_ids).hexdigest() == synclog.hash
