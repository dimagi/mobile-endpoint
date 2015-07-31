# -*- coding: utf-8 -*-
from uuid import UUID
import pytest
from mobile_endpoint.backends.manager import BACKEND_MONGO
from mobile_endpoint.backends.mongo.models import MongoSynclog
from tests.conftest import mongo
from tests.test_restore import RestoreTestMixin


@pytest.mark.usefixtures("testapp", "client", "mongodb", "db_reset")
@mongo
class TestMongoRestore(RestoreTestMixin):

    def _get_backend(self):
        return BACKEND_MONGO

    def _get_one_synclog(self):
        return MongoSynclog.objects.first()

    def _get_synclog_by_previous_id(self, id):
        MongoSynclog.objects(previous_log_id=UUID(id)).first()

    def _get_all_synclogs(self):
        return MongoSynclog.objects.all()

    def _get_restore_url_snippet(self):
        return 'mongo-restore'
