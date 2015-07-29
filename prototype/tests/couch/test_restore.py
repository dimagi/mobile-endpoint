# -*- coding: utf-8 -*-
import pytest
from tests.test_restore import RestoreTestMixin


@pytest.mark.usefixtures("testapp", "client", "db_reset")
class TestSQLRestore(RestoreTestMixin):

    def _get_backend(self):
        return 'couch'
