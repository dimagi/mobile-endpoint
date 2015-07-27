from __future__ import print_function
import contextlib
import json
import os
import sh
import sys
import settings


def get_psql(backend):
    pg_conf = {
        'p': settings.BACKENDS[backend]['PG_PORT'],
        'd': settings.BACKENDS[backend]['PG_DATABASE'],
        'U': settings.BACKENDS[backend]['PG_USERNAME'],
    }

    if settings.BACKENDS[backend]['PG_HOST']:
        pg_conf['h'] = settings.BACKENDS[backend]['PG_HOST']

    return sh.psql.bake(**pg_conf)


def execute_sql_file(psql, file):
    with open(os.path.join(settings.SQLDIR, file)) as f:
        return psql(_in=f)


def load_json(filename):
    with open(os.path.join(settings.JSONDIR, filename)) as f:
        return json.load(f)


def escape_json(doc):
    return json.dumps(doc).replace('"', '""')


def confirm(msg):
    return raw_input("{} [y/n] ".format(msg)).lower() == 'y'


def json_format_datetime(dt):
    return dt.strftime('%Y-%m-%dT%H:%M:%S.%fZ')


@contextlib.contextmanager
def cd(path):
    """http://stackoverflow.com/a/24469659
    """
    old_path = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old_path)

def update_progress(title, progress):
    print('\r{} [{}] {}%'.format(title, '#'*int(progress*50), int(progress*100)), end='')
