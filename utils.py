import json
import os
import sh
import settings


def get_psql():
    pg_conf = {
        'p': settings.PG_PORT,
        'd': settings.PG_DATABASE,
        'U': settings.PG_USERNAME,
    }

    if settings.PG_HOST:
        pg_conf['h'] = settings.PG_HOST

    return sh.psql.bake(**pg_conf)


psql = get_psql()


def execute_query(query):
    return psql("-A -t", c=query)


def execute_file(path):
    with open(path) as f:
        return psql(_in=f)


def load_json_escaped(filename):
    with open(os.path.join(settings.JSONDIR, filename)) as f:
        return json.dumps(json.load(f)).replace('"', '""')


def confirm(msg):
    return raw_input("{} [y/n] ".format(msg)).lower() == 'y'
