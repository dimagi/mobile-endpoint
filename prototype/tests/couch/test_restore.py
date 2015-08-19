# -*- coding: utf-8 -*-
import pytest
from mobile_endpoint.backends.couch.models import CouchSynclog
from mobile_endpoint.backends.manager import BACKEND_COUCH
from tests.conftest import couch
from tests.test_restore import RestoreTestMixin


@pytest.mark.usefixtures("testapp", "client", "couchdb", "couch_reset")
@couch
class TestCouchRestore(RestoreTestMixin):

    def _get_backend(self):
        return BACKEND_COUCH

    def _get_restore_url_snippet(self):
        return 'couch-restore'

    def _get_all_synclogs(self):
        return [
            log.to_generic() for log in CouchSynclog.view('_all_docs', include_docs=True)
            if not log._id.startswith('_design')
        ]

    def _get_one_synclog(self):
        for doc in CouchSynclog.view('_all_docs', include_docs=True):
            if not doc._id.startswith("_design"):
                return doc.to_generic()

    def _get_synclog_by_previous_id(self, id):
        return CouchSynclog.view(
            'synclogs/by_previous_log_id',
            key=id,
            include_docs=True,
            reduce=False,
        ).one().to_generic()
