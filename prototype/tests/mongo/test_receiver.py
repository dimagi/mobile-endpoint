import pytest
from mobile_endpoint.backends.mongo.models import MongoForm, MongoCase
from mobile_endpoint.backends.manager import BACKEND_MONGO
from tests.conftest import couch
from tests.test_receiver import ReceiverTestMixin, DOMAIN


@pytest.mark.usefixtures("testapp", "client", "mongodb", "db_reset")
@couch
class TestMongoReceiver(ReceiverTestMixin):
    # TODO: This test is very simillar to the couch test. Reuse some code?

    def _get_backend(self):
        return BACKEND_MONGO

    def _assert_form(self, form_id, user_id, synclog_id=None):
        form = MongoForm.get(form_id)
        assert form is not None
        assert form.domain == DOMAIN
        assert form.user_id == user_id
        if synclog_id:
            assert form.synclog_id == synclog_id
        else:
            assert form.synclog_id is None

    def _assert_case(self, case_id, owner_id, num_forms=1, closed=False, indices=None):
        mongo_case = MongoCase.get(case_id)
        assert mongo_case is not None
        assert mongo_case.domain == DOMAIN
        assert mongo_case.closed == closed
        # assert len(couch_case.forms) == num_forms
        assert mongo_case.owner_id == owner_id

        if indices:
            couch_indices = {}
            for index in mongo_case.indices:
                couch_indices[index['identifier']] = {
                    'referenced_type': index['referenced_type'],
                    'referenced_id': index['referenced_id']
                }
                assert couch_indices == indices

        return mongo_case

    def _assert_synclog(self, id, case_ids=None, dependent_ids=None, index_tree=None):
        # todo
        pass


