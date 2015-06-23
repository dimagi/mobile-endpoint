import os

from invoke import task
import sh

from utils import execute_file, confirm
import settings
from load_db import load_data
from db_to_csv import load_csv


@task
def tsung_hammer():
    tsung_build()
    tsung_erl_build()
    tsung_db()


@task
def tsung_build():
    from jinja2 import Environment, PackageLoader
    env = Environment(loader=PackageLoader('tsung', 'templates'))

    tsung_dir = os.path.join(settings.BASEDIR, 'tsung')

    context = {
        'dtd_path': settings.TSUNG_DTD_PATH,
        'duration': settings.TSUNG_DURATION,
        'arrival_rate': settings.TSUNG_USERS_PER_SECOND,
        'casedb': os.path.join(tsung_dir, 'files', 'casedb.csv'),
        'formdb': os.path.join(tsung_dir, 'files', 'formdb.csv'),
        'transactions_dir': os.path.join(tsung_dir, 'transactions'),
        'pg_host': settings.PG_HOST,
        'pg_port': settings.PG_PORT,
        'pg_database': settings.PG_DATABASE,
        'pg_username': settings.PG_USERNAME,
    }
    for filename in os.listdir(os.path.join(tsung_dir, 'templates')):
        if filename.endswith('j2'):
            template = env.get_template(filename)
            new_filename = os.path.join(tsung_dir, 'build', filename[:-3])
            with open(new_filename, 'w') as f:
                f.write(template.render(**context))
                print("Built config: {}".format(new_filename))


@task
def tsung_erl_compile():
    erlc = sh.Command('erlc')
    erl_dir = os.path.join(settings.BASEDIR, 'tsung', 'erlang_subst')
    erlc('-o', erl_dir, sh.glob(os.path.join(erl_dir, '*.erl')))
    print('Successfully compiled erl files')


@task
def tsung_erl_clean():
    erl_dir = os.path.join(settings.BASEDIR, 'tsung', 'erlang_subst')
    try:
        sh.rm(sh.glob(os.path.join(erl_dir, '*.beam')))
    except sh.ErrorReturnCode_1, e:
        print(e)
        print('There\'s probably nothing to clean, try running tsung_erl_compile')
    print('Successfully cleaned beam files')


@task
def tsung_erl_link():
    erl_dir = os.path.join(settings.BASEDIR, 'tsung', 'erlang_subst')
    sh.ln('-sf', sh.glob(os.path.join(erl_dir, '*.beam')), settings.TSUNG_EBIN)
    print('Successfully linked beam files')


@task
def tsung_erl_build():
    tsung_erl_clean()
    tsung_erl_compile()
    tsung_erl_link()


@task
def tsung_db(limit=10):
    """Builds the casedb.csv and formdb.cvs for tsung to reference using existing data in the database"""
    load_csv(limit)


@task
def load_db(scale):
    try:
        scale = int(scale)
    except ValueError:
        print("Scale must be an integer")

    forms = settings.SCALE_FACTOR * scale
    forms_with_cases = forms * settings.FORM_CASE_RATIO
    new_cases = int(forms_with_cases * settings.NEW_UPDATE_CASE_RATIO)
    case_updates = int(forms_with_cases * (1 - settings.NEW_UPDATE_CASE_RATIO))
    case_indexes = int(new_cases * settings.CHILD_CASE_RATIO)
    print("Loading data. Estimated numbers:")
    print("  formdata rows:  ", forms)
    print("  casedata rows:  ", new_cases)
    print("  caseindex rows: ", case_indexes)
    print("  case_form rows: ", new_cases + case_updates)

    load_data(scale)


@task
def init_db():
    def get_sql_file_path(name):
        return os.path.join(settings.SQLDIR, name)

    if not confirm("This will wipe any data in the database. Continue?"):
        print("Aborting.")
    else:
        print execute_file(get_sql_file_path('data_model.sql'))
