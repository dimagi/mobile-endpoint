# -*- coding: utf-8 -*-
import pytest
from mobile_endpoint.backends.manager import BACKEND_COUCH
from tests.conftest import couch
from tests.test_restore import RestoreTestMixin


@pytest.mark.usefixtures("testapp", "client", "couchdb", "db_reset")
@couch
class TestCouchRestore(RestoreTestMixin):

    def _get_backend(self):
        return BACKEND_COUCH

    def _get_restore_url_snippet(self):
        return 'couch-restore'
