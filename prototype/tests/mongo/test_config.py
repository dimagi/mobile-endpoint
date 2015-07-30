import uuid
import pytest
from mobile_endpoint.backends.mongo.models import MongoForm
from tests.conftest import mongo


@pytest.mark.usefixtures("testapp", "mongodb")
@mongo
class TestConfig(object):

    def test_setting(self, testapp):
        assert testapp.config.get('MONGO_URI')

    def test_db_works(self, testapp):
        with testapp.app_context():
            id = uuid.uuid4()
            collection = MongoForm.get_collection()
            collection.insert_one({'_id': id, 'prop': 'value'})
            doc = collection.find_one({'_id': id})
            assert doc['prop'] == 'value'
            collection.remove(doc)
            assert collection.find_one({'_id': id}) is None
