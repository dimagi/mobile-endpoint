import os
import sys

from invoke import task
import sh
import backends
import settings
from utils import confirm


def _get_backend(backend_name):
    return {
        "current": backends.Current,
        "prototype": backends.Prototype,
    }[backend_name]()


@task
def tsung_hammer():
    tsung_build()
    tsung_erl_build()
    populate_case_ids()


@task
def tsung_build(backend_name, user_rate=None, duration=None):
    from jinja2 import Environment, PackageLoader
    env = Environment(loader=PackageLoader('tsung', 'templates'))

    tsung_dir = os.path.join(settings.BASEDIR, 'tsung')
    build_dir = os.path.join(tsung_dir, 'build')
    if not os.path.isdir(build_dir):
        os.makedirs(build_dir)

    backend = _get_backend(backend_name)

    context = {
        'dtd_path': settings.TSUNG_DTD_PATH,
        'duration': duration or settings.TSUNG_DURATION,
        'arrival_rate': user_rate or settings.TSUNG_USERS_PER_SECOND,
        'casedb': os.path.join(tsung_dir, 'files', 'casedb.csv'),
        'host': backend.settings['HOST'],
        'port': backend.settings['PORT'],
        'submission_url': backend.submission_url,
        'username': backend.settings['USERNAME'],
        'domain': settings.DOMAIN,
        'user_id': backend.settings['USER_ID'],
        'create_submission': os.path.join(settings.BASEDIR, 'forms', 'create.xml'),
        'update_submission': os.path.join(settings.BASEDIR, 'forms', 'update.xml'),
    }
    for filename in os.listdir(os.path.join(tsung_dir, 'templates')):
        if filename.endswith('j2'):
            template = env.get_template(filename)
            new_filename = os.path.join(build_dir, filename[:-3])
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
def populate_case_ids(backend_name):
    """Builds casedb.csv for tsung to reference using existing data in the database"""
    _get_backend(backend_name).populate_case_csv(
        settings.NUM_CASES_TO_UPDATE,
        os.path.join(settings.BASEDIR, 'tsung/files/casedb.csv'),
    )


@task
def load_db(scale, backend_name):
    # TODO: Create the app and form and user

    try:
        scale = int(scale)
    except ValueError:
        print("Scale must be an integer")

    backend = _get_backend(backend_name)
    if confirm("Do you want to delete the current database?"):
        backend.reset_db()
    backend.load_data(scale)


@task
def awesome_test(backend, user_rate, duration, load=0, log_dir=None):
    if load:
        load_db(load, backend)
    tsung_build(backend, user_rate, duration)
    tsung_erl_build()
    if load:
        # Don't rebuild casedb.csv if the database wasn't reloaded.
        populate_case_ids(backend)
    args = ("-f", "tsung/build/tsung-hq-test.xml", "start")
    if log_dir:
        # TODO: Probably this needs to go before "start"
        args = args + ("-l", log_dir)
    for line in sh.tsung(*args, _iter=True):
        sys.stdout.write(line)
    # TODO: Build the report
