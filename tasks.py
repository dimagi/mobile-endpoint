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
        "prototype-sql": backends.PrototypeSQL,
    }[backend_name]()


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
        'userdb': os.path.join(tsung_dir, 'files', 'userdb.csv'),
        'host': backend.settings['HOST'],
        'port': backend.settings['PORT'],
        'submission_url': backend.submission_url,
        'domain': settings.DOMAIN,
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
def load_db(backend_name):
    files_dir = os.path.join(settings.BASEDIR, 'tsung', 'files')
    if not os.path.isdir(files_dir):
        os.makedirs(files_dir)

    backend = _get_backend(backend_name)
    if confirm("Do you want to delete the current database?"):
        backend.reset_db()
        print('Bootstrapping service with domain and superuser')
        backend.bootstrap_service()
        print('Creating test users')
        users = backend.create_users(settings.NUM_UNIQUE_USERS)

        user_db = os.path.join(files_dir, 'userdb.csv')
        with open(user_db, "w") as file:
            for user in users:
                file.write("{},{},{}\n".format(
                    user.id, user.username, user.password
                ))

    backend.load_data(files_dir)


@task
def awesome_test(backend, user_rate, duration, load=False, log_dir=None):
    if load:
        load_db(backend)
    tsung_build(backend, user_rate, duration)
    args = ("-f", "tsung/build/tsung-hq-test.xml", "start")
    if log_dir:
        # TODO: Probably this needs to go before "start"
        args = args + ("-l", log_dir)
    try:
        for line in sh.tsung(*args, _iter=True):
            sys.stdout.write(line)
    except Exception as e:
        print(e.stderr)
    # TODO: Build the report
