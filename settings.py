import os

BASEDIR = os.path.abspath(os.path.dirname(__file__))
JSONDIR = os.path.join(BASEDIR, "json")
SQLDIR = os.path.join(BASEDIR, "sql")

BACKENDS = {
    'current': {
        'SUBMISSION_URL': '/a/{domain}/receiver/',
        'HOST': 'localhost',
        'PORT': '8000',

        # These must match the values in the Django localsettings.py file
        'COUCH_HOST': 'localhost',
        'COUCH_PORT': '5984',
        'COUCH_DATABASE': 'hq_load_test',
        'COUCH_USERNAME': 'commcarehq',
        'COUCH_PASSWORD': 'commcarehq',

        # These must match the values in the Django localsettings.py file
        'PG_HOST': 'localhost',
        'PG_PORT': '5432',
        'PG_DATABASE': 'hq_load_test',
        'PG_USERNAME': 'postgres',

        'SUPERUSER_USERNAME': 'joe@dimagi.com',
        'SUPERUSER_PASSWORD': 'mater'
    },
    'prototype-sql': {
        'SUBMISSION_URL': '/ota/receiver',
        'HOST': 'localhost',
        'PORT': '5000',

        # Must match the values in localconfig.py file
        'PG_HOST': 'localhost',
        'PG_PORT': '5432',
        'PG_DATABASE': 'prototype_load_test',
        'PG_USERNAME': 'postgres',
    },
}

DOMAIN = 'load-test-domain'

##### SCALE FACTORS #####
# Number of uses to test against
NUM_UNIQUE_USERS = 100

# Number of cases to create per user
CASES_PER_USER = 1500

# Number of forms to be submitted against each case
FORMS_PER_CASE = 1.5

# Of the cases that are created what ratio are child cases
CHILD_CASE_RATIO = 0.5

##### TEST FACTORS ####
# The number of different cases that will updated during the tests.
NUM_CASES_TO_UPDATE = 10000


### Bootstrap settings ###
TEST_SERVER = 'indiacloud8.internal.commcarehq.org'
HQ_ENVIRONMENT_ROOT = '/home/cchq/www/tsung_hq_test/code_root'
PYTHONN_ENV = '/home/cchq/www/tsung_hq_test/python_env'
MOBILE_USER_PASSWORD = '123'


##### TSUNG CONFIG #####
TSUNG_DURATION = 600  # Default test length in seconds. Override via command line
TSUNG_USERS_PER_SECOND = 15  # Default user arrival rate per second. Override via command line


try:
    from localsettings import *
except ImportError:
    pass
