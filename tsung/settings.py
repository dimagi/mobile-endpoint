import os

BASEDIR = os.path.abspath(os.path.dirname(__file__))
TEMPLATE_DIR = os.path.join(BASEDIR, 'templates')
BUILD_DIR = os.path.join(BASEDIR, 'build')
DB_FILES_DIR = os.path.join(BUILD_DIR, 'files')
JSON_DIR = os.path.join(TEMPLATE_DIR, "json")
SQLDIR = os.path.join(BASEDIR, 'sql')
RAW_TRANSACTION_DIR_NAME = "raw_transactions"

ENDPOINTS = {
    'icds-cas': {
        'BACKEND': 'production',
        'SUBMISSION_URL': '/a/{domain}/receiver/',
        'RESTORE_URL': '/a/{domain}/phone/restore/',
        'SUBMIT_WITH_AUTH': True,
        'HTTPS': True,
        'HOST': 'www.icds-cas.gov.in',

        'SUPERUSER_USERNAME': '',
        'SUPERUSER_PASSWORD': '',

        'DOMAIN': ''
    }
}

TEST_RUNS = {
    'baseline': {
        'session_probabilities': {
             # must add up to 100
            'simple_form': 100,
            'create_case': 0,
            'update_case': 0,
            'restore': 0,
            'auth': 0
         },
        'phases':[
            {'duration': 60 * 5, 'user_arrival_rate': 20},
            {'duration': 60 * 5, 'user_arrival_rate': 40},
            {'duration': 60 * 5, 'user_arrival_rate': 60},
            {'duration': 60 * 5, 'user_arrival_rate': 80},
        ]
    }
}


MOBILE_USER_PASSWORD = '123'

##### TSUNG CONFIG #####
TSUNG_DTD_PATH = '/usr/local/src/tsung/tsung-1.0.dtd'

try:
    from localsettings import *
except ImportError:
    pass
