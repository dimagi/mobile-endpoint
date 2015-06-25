import os

BASEDIR = os.path.abspath(os.path.dirname(__file__))
SQLDIR = os.path.join(BASEDIR, "sql")
JSONDIR = os.path.join(BASEDIR, "json")

PG_HOST = ""
PG_PORT = ""
PG_DATABASE = ""
PG_USERNAME = ""

HQ_HOST = ""
HQ_PORT = ""
HQ_APP_ID = ""

##### SCALE FACTORS #####
# see "load_db.py" for how these relate to real numbers of rows

# multiplication factor for load_db command
SCALE_FACTOR = 10000

# ratio of forms that create or update a case
FORM_CASE_RATIO = 0.6

# Ratio of new cases to case updates
NEW_UPDATE_CASE_RATIO = 0.5

# of the cases that are created what ratio are child cases
CHILD_CASE_RATIO = 0.5

DOMAIN = 'test_domain'

##### TSUNG CONFIG #####
TSUNG_DTD_PATH = '/usr/local/src/tsung/tsung-1.0.dtd'
TSUNG_EBIN = '/usr/local/src/tsung/ebin'
TSUNG_DURATION = 600  # Test length in seconds
TSUNG_USERS_PER_SECOND = 15


try:
    from localsettings import *
except ImportError:
    pass
