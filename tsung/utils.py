from __future__ import print_function
import contextlib
import json
import os

import sh
import settings


def get_psql(backend):
    pg_conf = {
        'p': settings.PG_PORT,
        'd': settings.BACKENDS[backend]['PG_DATABASE'],
        'U': settings.PG_USERNAME,
    }

    if settings.PG_HOST:
        pg_conf['h'] = settings.PG_HOST

    return sh.psql.bake(**pg_conf)


def execute_sql_file(psql, file):
    print(os.path.join(settings.SQLDIR, file))
    return psql(f=os.path.join(settings.SQLDIR, file))


def load_json(filename):
    with open(os.path.join(settings.JSON_DIR, filename)) as f:
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


def get_settings_for_readme():
    out = []
    for name in ['NUM_UNIQUE_USERS', 'CASES_PER_USER', 'FORMS_PER_CASE', 'CHILD_CASE_RATIO', 'NUM_CASES_TO_UPDATE']:
        out.append('{} = {}'.format(name, getattr(settings, name)))

    return '\n'.join(out)
