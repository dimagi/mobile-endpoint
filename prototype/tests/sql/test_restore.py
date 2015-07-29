# -*- coding: utf-8 -*-
import pytest
from tests.conftest import sql
from tests.test_restore import RestoreTestMixin


@pytest.mark.usefixtures("testapp", "client", "sqldb", "db_reset")
@sql
class TestSQLRestore(RestoreTestMixin):

    def _get_backend(self):
        return 'sql'
