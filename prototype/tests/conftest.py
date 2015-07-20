import pytest
import os
import sys


def _set_source_root_parent(source_root_parent):
    """
    add everything under `source_root_parent` to the list of source roots
    e.g. if you call this with param 'submodules'
    and you have the file structure

    project/
        submodules/
            foo-src/
                foo/
            bar-src/
                bar/

    (where foo and bar are python modules)
    then foo and bar would become top-level importable

    """
    filedir = os.path.dirname(__file__)
    submodules_list = os.listdir(os.path.join(filedir, source_root_parent))
    for d in submodules_list:
        if d == "__init__.py" or d == '.' or d == '..':
            continue
        sys.path.insert(1, os.path.join(filedir, source_root_parent, d))

    sys.path.append(os.path.join(filedir, source_root_parent))

_set_source_root_parent('../submodules')

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
        with db.session.begin():
            for table in reversed(db.Model.metadata.sorted_tables):
                db.session.execute(table.delete())

        db.session.remove()

    request.addfinalizer(teardown)


@pytest.fixture()
def client(testapp):
    return testapp.test_client()
