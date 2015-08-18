# -*- coding: utf-8 -*-
import pytest
from mobile_endpoint.backends.couch.models import CouchSynclog
from mobile_endpoint.backends.manager import BACKEND_COUCH
from tests.conftest import couch
from tests.test_restore import RestoreTestMixin


@pytest.mark.usefixtures("testapp", "client", "couchdb")
@couch
class TestCouchRestore(RestoreTestMixin):

    def _get_backend(self):
        return BACKEND_COUCH

    def _get_restore_url_snippet(self):
        return 'couch-restore'

    def _get_all_synclogs(self):
        return [log.to_generic() for log in CouchSynclog.view('_all_docs', include_docs=True)]

    def _get_one_synclog(self):
        return CouchSynclog.view('_all_docs', include_docs=True).first().to_generic()

    def _get_synclog_by_previous_id(self, id):
        raise NotImplementedError
