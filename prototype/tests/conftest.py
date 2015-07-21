import pytest
from patch_path import patch_path
patch_path()

from mobile_endpoint import create_app
from mobile_endpoint.models import db


@pytest.fixture(scope="session")
def testapp():
    app = create_app('testconfig.py')

    db.app = app
    db.create_all()

    return app


@pytest.fixture()
def db_reset(request):
    def teardown():
        for table in reversed(db.Model.metadata.sorted_tables):
            db.session.execute(table.delete())

        db.session.commit()
        db.session.remove()

    request.addfinalizer(teardown)


@pytest.fixture()
def client(testapp):
    return testapp.test_client()
