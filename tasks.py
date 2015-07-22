import os

from invoke import task
import sh
import sys

import settings
from load_db import load_data
from db_to_csv import load_csv


@task
def tsung_hammer():
    tsung_build()
    tsung_erl_build()
    tsung_db()


@task
def tsung_build(user_rate=None, duration=None):
    from jinja2 import Environment, PackageLoader
    env = Environment(loader=PackageLoader('tsung', 'templates'))

    tsung_dir = os.path.join(settings.BASEDIR, 'tsung')

    context = {
        'dtd_path': settings.TSUNG_DTD_PATH,
        'duration': duration or settings.TSUNG_DURATION,
        'arrival_rate': user_rate or settings.TSUNG_USERS_PER_SECOND,
        'casedb': os.path.join(tsung_dir, 'files', 'casedb.csv'),
        'hq_host': settings.HQ_HOST,
        'hq_port': settings.HQ_PORT,
        'hq_app_id': settings.HQ_APP_ID,
        'couch_host': settings.COUCH_HOST,
        'couch_port': settings.COUCH_PORT,
        'username': settings.USERNAME,
        'domain': settings.DOMAIN,
        'user_id': settings.USER_ID,
        'create_submission': os.path.join(settings.BASEDIR, 'forms', 'create.xml'),
        'update_submission': os.path.join(settings.BASEDIR, 'forms', 'update.xml'),
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
def tsung_db():
    """Builds casedb.csv for tsung to reference using existing data in the database"""
    load_csv(settings.NUM_CASES_TO_UPDATE)

@task
def load_db(scale):
    # TODO: Create the app and form and user

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
def awesome_test(test_name, user_rate, duration, load=0, log_dir=None):
    if load:
        load_db(load)
    tsung_build(user_rate, duration)
    tsung_erl_build()
    if load:
        # Don't rebuild casedb.csv if the database wasn't reloaded.
        tsung_db()
    args = ("-f", "tsung/build/{}.xml".format(test_name), "start")
    if log_dir:
        args = args + ("-l", log_dir)
    for line in sh.tsung(*args, _iter=True):
        sys.stdout.write(line)
    # TODO: Build the report
