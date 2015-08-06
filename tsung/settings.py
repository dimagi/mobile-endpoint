import os

BASEDIR = os.path.abspath(os.path.dirname(__file__))
TEMPLATE_DIR = os.path.join(BASEDIR, 'templates')
BUILD_DIR = os.path.join(BASEDIR, 'build')
DB_FILES_DIR = os.path.join(BUILD_DIR, 'files')
JSON_DIR = os.path.join(TEMPLATE_DIR, "json")

BACKENDS = {
    'current': {
        'SUBMISSION_URL': '/a/{domain}/receiver/',
        'SUBMIT_WITH_AUTH': False,
        'HOST': '10.10.1.28',
        'PORT': '9010',

        # These must match the values in the Django localsettings.py file
        'COUCH_HOST': '10.10.1.28',
        'COUCH_PORT': '5984',
        'COUCH_DATABASE': 'commcarehq',
        'COUCH_USERNAME': 'commcarehq',
        'COUCH_PASSWORD': 'commcarehq',

        # These must match the values in the Django localsettings.py file
        'PG_HOST': '10.10.1.28',
        'PG_PORT': '5432',
        'PG_DATABASE': 'commcarehq',
        'PG_USERNAME': 'commcarehq',

        'SUPERUSER_USERNAME': 'load_test@dimagi.com',
        'SUPERUSER_PASSWORD': 'load_test',

        'ENVIRONMENT_ROOT': '/home/cchq/www/tsung_hq_test/code_root',
        'PYTHON_ENV': '/home/cchq/www/tsung_hq_test/python_env',
    },
    'prototype-sql': {
        'SUBMISSION_URL': '/ota/receiver/{domain}',
        'SUBMIT_WITH_AUTH': True,
        'HOST': '10.10.1.28',
        'PORT': '9011',

        # Must match the values in localconfig.py file
        'PG_HOST': '10.10.1.28',
        'PG_PORT': '5432',
        'PG_DATABASE': 'prototype_sql',
        'PG_USERNAME': 'commcarehq',

        'ENVIRONMENT_ROOT': '/home/cchq/prototype/mobile-endpoint/prototype',
        'PYTHON_ENV': '/home/cchq/prototype/python_env',
    },
    'prototype-mongo': {
        'SUBMISSION_URL': '/ota/mongo-receiver/{domain}',
        'SUBMIT_WITH_AUTH': True,
        'HOST': '10.10.1.28',
        'PORT': '9011',

        'MONGO_URI': 'mongodb://10.10.1.28:27017/mobile_endpoint',
        # Mongo URI should include the database

        'PG_HOST': '10.10.1.28',
        'PG_PORT': '5432',
        'PG_DATABASE': 'prototype_sql',
        'PG_USERNAME': 'commcarehq',

        'ENVIRONMENT_ROOT': '/home/cchq/prototype/mobile-endpoint/prototype',
        'PYTHON_ENV': '/home/cchq/prototype/python_env',
    },
}

DOMAIN = 'load-test-domain'

##### SCALE FACTORS #####
# Number of uses to test against
NUM_UNIQUE_USERS = 10

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
MOBILE_USER_PASSWORD = '123'


##### TSUNG CONFIG #####
TSUNG_DTD_PATH = '/usr/local/src/tsung/tsung-1.0.dtd'

try:
    from localsettings import *
except ImportError:
    pass
