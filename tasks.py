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
def load_db(scale, backend_name):
    # TODO: Create the app and form and user

    try:
        scale = int(scale)
    except ValueError:
        print("Scale must be an integer")

    backend = _get_backend(backend_name)
    if confirm("Do you want to delete the current database?"):
        backend.reset_db()

    files_dir = os.path.join(settings.BASEDIR, 'tsung', 'files')
    if not os.path.isdir(files_dir):
        os.makedirs(files_dir)

    backend.load_data(scale, files_dir)


@task
def awesome_test(backend, user_rate, duration, load=0, log_dir=None):
    if load:
        load_db(load, backend)
    tsung_build(backend, user_rate, duration)
    args = ("-f", "tsung/build/tsung-hq-test.xml", "start")
    if log_dir:
        # TODO: Probably this needs to go before "start"
        args = args + ("-l", log_dir)
    for line in sh.tsung(*args, _iter=True):
        sys.stdout.write(line)
    # TODO: Build the report
