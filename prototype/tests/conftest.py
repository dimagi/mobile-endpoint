from flask.ext.migrate import upgrade
import pytest
from patch_path import patch_path
patch_path()

from mobile_endpoint import create_app
from mobile_endpoint.models import db


@pytest.fixture(scope="session")
def testapp():
    from mobile_endpoint.backends.couch.db import init_dbs
    app = create_app('testconfig.py')

    db.app = app
    with app.app_context():
        upgrade()
        # init couch DBs
        init_dbs()

    return app


@pytest.fixture()
def db_reset(request):
    def teardown():
        from mobile_endpoint.backends.couch.db import delete_db
        delete_all_data()
        db.session.remove()
        # todo: figure out how to get the context
        # delete_db('test')  # todo parameterize
    request.addfinalizer(teardown)


@pytest.fixture()
def client(testapp):
    return testapp.test_client()


def delete_all_data():
    with db.session.begin():
        for table in reversed(db.Model.metadata.sorted_tables):
            db.session.execute(table.delete())
