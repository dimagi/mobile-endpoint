import os

BASEDIR = os.path.abspath(os.path.dirname(__file__))
TEMPLATE_DIR = os.path.join(BASEDIR, 'templates')
BUILD_DIR = os.path.join(BASEDIR, 'build')
DB_FILES_DIR = os.path.join(BUILD_DIR, 'files')
JSON_DIR = os.path.join(TEMPLATE_DIR, "json")
SQLDIR = os.path.join(BASEDIR, 'sql')
RAW_TRANSACTION_DIR_NAME = "raw_transactions"

PG_HOST = '10.10.1.28'
PG_PORT = '5432'
PG_USERNAME = 'commcarehq'
PG_PASSWORD = ''

ENDPOINTS = {
    'current': {
        'BACKEND': 'production',
        'SUBMISSION_URL': '/a/{domain}/receiver/',
        'RESTORE_URL': '/a/{domain}/phone/restore/',
        'SUBMIT_WITH_AUTH': False,
        'HOST': '10.10.1.28',
        'PORT': '9010',  # Override the default (80 for HTTP and 443 for HTTPS)
        'HTTPS': False,

        'SUPERUSER_USERNAME': 'load_test@dimagi.com',
        'SUPERUSER_PASSWORD': 'load_test',

        'SESSION_PROBABILITIES': {
            # must add up to 100
            'simple_form': 0,
            'create_case': 45,
            'update_case': 45,
            'restore': 10
        }
    },
}

DOMAIN = 'load-test-domain'

##### SCALE FACTORS #####
# Number of uses to test against
NUM_UNIQUE_USERS = 150

# Number of cases to create per user
CASES_PER_USER = 100

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
