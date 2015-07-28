import os
import sys

from invoke import task
import sh

import backends
import settings
from utils import cd
from utils import confirm


def _get_backend(backend_name):
    return {
        "current": backends.Current,
        "prototype-sql": backends.PrototypeSQL,
    }[backend_name]()


@task
def tsung_build(backend_name, user_rate=None, duration=None):
    from jinja2 import Environment, FileSystemLoader
    env = Environment(loader=FileSystemLoader(settings.TEMPLATE_DIR))

    if not os.path.isdir(settings.BUILD_DIR):
        os.makedirs(settings.BUILD_DIR)

    backend = _get_backend(backend_name)

    context = {
        'dtd_path': settings.TSUNG_DTD_PATH,
        'duration': duration or settings.TSUNG_DURATION,
        'arrival_rate': user_rate or settings.TSUNG_USERS_PER_SECOND,
        'casedb': os.path.join(settings.DB_FILES_DIR, 'casedb.csv'),
        'userdb': os.path.join(settings.DB_FILES_DIR, 'userdb.csv'),
        'host': backend.settings['HOST'],
        'port': backend.settings['PORT'],
        'submission_url': backend.submission_url,
        'domain': settings.DOMAIN,
        'create_submission': os.path.join(settings.BASEDIR, 'forms', 'create.xml'),
        'update_submission': os.path.join(settings.BASEDIR, 'forms', 'update.xml'),
    }
    for filename in os.listdir(os.path.join(settings.BASEDIR, 'templates')):
        if filename.endswith('j2'):
            template = env.get_template(filename)
            new_filename = os.path.join(settings.BUILD_DIR, filename[:-3])
            with open(new_filename, 'w') as f:
                f.write(template.render(**context))
                print("Built config: {}".format(new_filename))


@task
def load_db(backend_name):
    if not os.path.isdir(settings.DB_FILES_DIR):
        os.makedirs(settings.DB_FILES_DIR)

    backend = _get_backend(backend_name)
    if confirm("Do you want to delete the current database?"):
        backend.check_access()
        backend.stop()
        backend.reset_db()
        print('Bootstrapping service with domain and superuser')
        backend.bootstrap_service()

        backend.start()
        print('Creating test users')
        users = backend.create_users(settings.NUM_UNIQUE_USERS)

        user_db = os.path.join(settings.DB_FILES_DIR, 'userdb.csv')
        with open(user_db, "w") as file:
            for user in users:
                file.write("{},{},{}\n".format(
                    user.id, user.username, user.password
                ))

    backend.load_data(settings.DB_FILES_DIR)


@task
def awesome_test(backend, user_rate, duration, load=False):
    if load:
        load_db(backend)

    tsung_build(backend, user_rate, duration)

    backend = _get_backend(backend)
    if not backend.is_running():
        backend.restart()

    log_dir = None
    args = ("-f", "build/tsung-hq-test.xml", "start")
    try:
        for line in sh.tsung(*args, _iter=True):
            sys.stdout.write(line)
            if 'Log directory' in line:
                log_dir = line.splint(':')[1]
    except Exception as e:
        print(e.stderr)

    if log_dir:
        title = 'Awesome Test: backend={}, user_rate={}, duration={}'.format(
            backend.name, user_rate, duration
        )
        with cd(log_dir):
            sh.Command('/usr/lib/tsung/bin/tsung_stats.pl')('--title', title)
