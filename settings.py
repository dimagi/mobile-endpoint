import os

BASEDIR = os.path.abspath(os.path.dirname(__file__))
JSONDIR = os.path.join(BASEDIR, "json")
SQLDIR = os.path.join(BASEDIR, "sql")

BACKENDS = {
    'current': {
        'SUBMISSION_URL': '',  # e.g. /{domain}/receiver/
        'HOST': '',
        'PORT': '',
        'USER_ID': '',
        'USERNAME': '',
        'PASSWORD': '',

        # HQ Couch DB
        'COUCH_HOST': '',
        'COUCH_PORT': '',
        'COUCH_DATABASE': '',
        'COUCH_USERNAME': '',
        'COUCH_PASSWORD': '',

        # HQ postgres DB
        'PG_HOST': '',
        'PG_PORT': '',
        'PG_DATABASE': '',
        'PG_USERNAME': '',

        # username and password for superuser (will get created during bootstrap)
        'SUPERUSER_USERNAME': '',
        'SUPERUSER_PASSWORD': ''
    },
    'prototype': {
        'SUBMISSION_URL': '',
        'HOST': '',
        'PORT': '',
        'USER_ID': '',
        'USERNAME': '',
        'PASSWORD': '',

        # Prototype postgres DB
        'PG_HOST': '',
        'PG_PORT': '',
        'PG_DATABASE': '',
        'PG_USERNAME': '',
    },
}

DOMAIN = ''

##### SCALE FACTORS #####
# see "loaders.py" for how these relate to real numbers of rows

# multiplication factor for load_db command
SCALE_FACTOR = 10000

# ratio of forms that create or update a case
FORM_CASE_RATIO = 0.6

# of the cases that are created what ratio are child cases
CHILD_CASE_RATIO = 0.5

NUM_UNIQUE_USERS = SCALE_FACTOR / 10

##### TEST FACTORS ####
# The number of different cases that will updated during the tests.
NUM_CASES_TO_UPDATE = 10000


### Bootstrap settings ###
TEST_SERVER = 'indiacloud8.internal.commcarehq.org'
HQ_ENVIRONMENT_ROOT = '/home/cchq/www/tsung_hq_test/code_root'
PYTHONN_ENV = '/home/cchq/www/tsung_hq_test/python_env'
MOBILE_USER_PASSWORD = '123'


##### TSUNG CONFIG #####
TSUNG_DURATION = 600  # Test length in seconds
TSUNG_USERS_PER_SECOND = 15


try:
    from localsettings import *
except ImportError:
    pass
