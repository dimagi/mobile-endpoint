import sh
import settings

pg_conf = {
    'p': settings.PG_PORT,
    'd': settings.PG_DATABASE,
    'U': settings.PG_USERNAME,
}

if settings.PG_HOST:
    pg_conf['h'] = settings.PG_HOST

psql = sh.psql.bake(**pg_conf)


def execute_query(query):
    return psql("-A -t", c=query)


def execute_file(path):
    with open(path) as f:
        return psql(_in=f)
