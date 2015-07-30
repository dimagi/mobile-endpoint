import uuid
import pytest
from mobile_endpoint.backends.mongo.models import MongoCase
from tests.conftest import mongo


@pytest.mark.usefixtures("testapp", "mongodb")
@mongo
class TestConfig(object):

    def test_setting(self, testapp):
        assert testapp.config.get('MONGO_URI')

    def test_db_works(self, testapp):
        with testapp.app_context():
            id = uuid.uuid4()
            case = MongoCase(id=id, prop='value')
            case.save()
            doc = MongoCase.objects.get(id=id)
            assert doc.prop == 'value'
            doc.delete()
