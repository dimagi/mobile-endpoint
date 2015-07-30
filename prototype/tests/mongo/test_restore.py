# -*- coding: utf-8 -*-
import pytest
from mobile_endpoint.backends.manager import BACKEND_MONGO
from tests.conftest import mongo
from tests.test_restore import RestoreTestMixin


@pytest.mark.usefixtures("testapp", "client", "mongodb", "db_reset")
@mongo
class TestCouchRestore(RestoreTestMixin):

    def _get_backend(self):
        return BACKEND_MONGO
