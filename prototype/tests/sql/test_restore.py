# -*- coding: utf-8 -*-
import pytest
from mobile_endpoint.backends.manager import BACKEND_SQL
from mobile_endpoint.models import Synclog
from tests.conftest import sql
from tests.test_restore import RestoreTestMixin


@pytest.mark.usefixtures("testapp", "client", "sqldb", "sql_reset")
@sql
class TestSQLRestore(RestoreTestMixin):

    def _get_backend(self):
        return BACKEND_SQL

    def _get_all_synclogs(self):
        return [s.to_generic() for s in Synclog.query.all()]

    def _get_one_synclog(self):
        return Synclog.query.one().to_generic()

    def _get_synclog_by_previous_id(self, id):
        return Synclog.query.filter(Synclog.previous_log_id == id).one().to_generic()

    def _get_restore_url_snippet(self):
        return 'restore'
