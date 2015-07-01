import pytest

from mobile_endpoint import create_app
from mobile_endpoint.models import db


@pytest.fixture()
def testapp(request):
    app = create_app()
    client = app.test_client()

    db.app = app
    db.create_all()

    def teardown():
        db.session.remove()
        db.drop_all()

    request.addfinalizer(teardown)

    return client
