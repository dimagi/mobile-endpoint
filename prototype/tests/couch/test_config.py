import pytest


@pytest.mark.usefixtures("testapp")
class TestConfig(object):

    def test_setting(self, testapp):
        assert testapp.config.get('COUCH_URI')

