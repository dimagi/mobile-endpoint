from flask import current_app
from flask.ext.migrate import upgrade
from mongoengine import connect
import pytest
from patch_path import patch_path
patch_path()

from mobile_endpoint import create_app
from mobile_endpoint.models import db

couch = pytest.mark.couch
sql = pytest.mark.sql
mongo = pytest.mark.mongo
rowsize = pytest.mark.rowsize


def pytest_addoption(parser):
    parser.addoption("--rowsize", action="store", metavar="model",
        help="only run row size tests")


def pytest_runtest_setup(item):
    rowsize_marker = item.get_marker("rowsize")
    run_rowsize_tests = item.config.getoption("--rowsize")
    if rowsize_marker:
        model = rowsize_marker.args[0]
        if not run_rowsize_tests:
            pytest.skip("need --rowsize option to run")
        if model != run_rowsize_tests:
            pytest.skip("only running tests for model: {}".format(run_rowsize_tests))
    elif run_rowsize_tests:
        pytest.skip("only running rowsize tests")


@pytest.fixture(scope="session")
def testapp():
    app = create_app('testconfig.py')

    db.app = app
    return app


@pytest.fixture(scope="session")
def sqldb(testapp):
    with testapp.app_context():
        upgrade()


@pytest.fixture(scope="session")
def couchdb(testapp):
    from mobile_endpoint.backends.couch.db import init_dbs
    with testapp.app_context():
        init_dbs()

@pytest.fixture(scope="session")
def mongodb(testapp):
    # Maybe we should delete everything here?
    # Makes more sense to do it in db_reset I think.
    with testapp.app_context():
        connect(host=current_app.config.get('MONGO_URI'))


@pytest.fixture()
def sql_reset(request):
    def teardown():
        # TODO: Get context or parameterize this fixture
        delete_all_data()
        db.session.remove()
    request.addfinalizer(teardown)


@pytest.fixture()
def mongo_reset(request):
    from mobile_endpoint.backends.mongo.models import MongoForm, MongoCase, MongoSynclog
    def teardown():
        MongoForm._get_collection().drop()
        MongoCase._get_collection().drop()
        MongoSynclog._get_collection().drop()
    request.addfinalizer(teardown)


@pytest.fixture()
def client(testapp):
    return testapp.test_client()


def delete_all_data():
    with db.session.begin():
        for table in reversed(db.Model.metadata.sorted_tables):
            db.session.execute(table.delete())
