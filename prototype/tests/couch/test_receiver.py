import pytest
from mobile_endpoint.backends.couch.models import CouchForm, CouchCase
from mobile_endpoint.backends.manager import BACKEND_COUCH
from tests.conftest import couch
from tests.test_receiver import ReceiverTestMixin, DOMAIN


@pytest.mark.usefixtures("testapp", "client", "couchdb", "db_reset")
@couch
class TestCouchReceiver(ReceiverTestMixin):

    def _get_backend(self):
        return BACKEND_COUCH

    def _assert_form(self, form_id, user_id, synclog_id=None):
        form = CouchForm.get(form_id)
        assert form is not None
        assert form.domain == DOMAIN
        assert form.user_id == user_id
        if synclog_id:
            assert form.synclog_id == synclog_id
        else:
            assert form.synclog_id is None

    def _assert_case(self, case_id, owner_id, num_forms=1, closed=False, indices=None):
        couch_case = CouchCase.get(case_id)
        assert couch_case is not None
        assert couch_case.domain == DOMAIN
        assert couch_case.closed == closed
        # assert len(couch_case.forms) == num_forms
        assert couch_case.owner_id == owner_id

        if indices:
            couch_indices = {}
            for index in couch_case.indices:
                couch_indices[index['identifier']] = {
                    'referenced_type': index['referenced_type'],
                    'referenced_id': index['referenced_id']
                }
            assert couch_indices == indices

        return couch_case

    def _assert_synclog(self, id, case_ids=None, dependent_ids=None, index_tree=None):
        # todo
        pass


