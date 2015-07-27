import uuid
import pytest
from mobile_endpoint.backends.couch.db import get_db


@pytest.mark.usefixtures("testapp")
class TestConfig(object):

    def test_setting(self, testapp):
        assert testapp.config.get('COUCH_URI')

    def test_db_works(self, testapp):
        with testapp.app_context():
            id = uuid.uuid4().hex
            db = get_db('test')
            db.save_doc({'_id': id, 'prop': 'value'})
            doc = db.get(id)
            assert doc['prop'] == 'value'
            assert doc['_rev']
            db.delete_doc(doc)
