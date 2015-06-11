import os

BASEDIR = os.path.abspath(os.path.dirname(__file__))
SQLDIR = os.path.join(BASEDIR, "sql")

PG_HOST = ""
PG_PORT = ""
PG_DATABASE = ""
PG_USERNAME = ""

try:
    from localsettings import *
except ImportError:
    pass
