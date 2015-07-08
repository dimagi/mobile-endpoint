import os

from invoke import task
import sh

import settings
from load_db import load_data


@task
def tsung_hammer():
    tsung_build()
    tsung_erl_build()


@task
def tsung_build():
    from jinja2 import Environment, PackageLoader
    env = Environment(loader=PackageLoader('tsung', 'templates'))

    tsung_dir = os.path.join(settings.BASEDIR, 'tsung')

    context = {
        'dtd_path': settings.TSUNG_DTD_PATH,
        'duration': settings.TSUNG_DURATION,
        'arrival_rate': settings.TSUNG_USERS_PER_SECOND,
        'hq_host': settings.HQ_HOST,
        'hq_port': settings.HQ_PORT,
        'hq_app_id': settings.HQ_APP_ID,
        'username': settings.USERNAME,
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
