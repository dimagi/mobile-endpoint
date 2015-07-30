from uuid import UUID
import pytest
from mobile_endpoint.backends.mongo.models import MongoForm, MongoCase, \
    MongoSynclog
from mobile_endpoint.backends.manager import BACKEND_MONGO
from mobile_endpoint.synclog.checksum import Checksum
from tests.conftest import mongo
from tests.test_receiver import ReceiverTestMixin, DOMAIN


@pytest.mark.usefixtures("testapp", "client", "mongodb", "db_reset")
@mongo
class TestMongoReceiver(ReceiverTestMixin):
    # TODO: This test is very simillar to the couch test. Reuse some code?
    # TODO: Clear the mongodb before use?

    def _get_backend(self):
        return BACKEND_MONGO

    def _assert_form(self, form_id, user_id, synclog_id=None):
        form = MongoForm.objects.get(id=form_id)
        assert form is not None
        assert form.domain == DOMAIN
        assert form.user_id == UUID(user_id)
        if synclog_id:
            assert form.synclog_id == UUID(synclog_id)
        else:
            assert form.synclog_id is None

    def _assert_case(self, case_id, owner_id, num_forms=1, closed=False, indices=None):
        mongo_case = MongoCase.objects.get(id=case_id)
        assert mongo_case is not None
        assert mongo_case.domain == DOMAIN
        assert mongo_case.closed == closed
        # assert len(couch_case.forms) == num_forms
        assert mongo_case.owner_id == UUID(owner_id)

        if indices:
            mongo_indices = {}
            for index in mongo_case.indices:
                mongo_indices[index['identifier']] = {
                    'referenced_type': index['referenced_type'],
                    'referenced_id': UUID(index['referenced_id'])
                }
                assert mongo_indices == indices

        return mongo_case

    def _assert_synclog(self, id, case_ids=None, dependent_ids=None, index_tree=None):
        synclog = MongoSynclog.objects.get(id=id)
        case_ids = case_ids or []
        dependent_ids = dependent_ids or []
        index_tree = index_tree or {}
        assert case_ids == [unicode(i) for i in synclog.case_ids_on_phone]
        assert dependent_ids == [unicode(i) for i in synclog.dependent_case_ids_on_phone]
        assert index_tree == synclog.index_tree
        assert Checksum(case_ids).hexdigest() == unicode(synclog.hash)

