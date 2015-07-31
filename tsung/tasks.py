from collections import namedtuple
import os
import sys

from invoke import task
import sh

import backends
import settings
from utils import cd, get_settings_for_readme
from utils import confirm

Phase = namedtuple('Phase', 'duration, arrival_rate')


def _get_backend(backend_name):
    return {
        "current": backends.Current,
        "prototype-sql": backends.PrototypeSQL,
    }[backend_name]()


def _render_template(filename, context):
    from jinja2 import Environment, FileSystemLoader
    env = Environment(loader=FileSystemLoader(settings.TEMPLATE_DIR))
    template = env.get_template(filename)
    return template.render(**context)


@task
def tsung_build(backend_name, user_rate=None, duration=None):
    if not os.path.isdir(settings.BUILD_DIR):
        os.makedirs(settings.BUILD_DIR)

    backend = _get_backend(backend_name)
    duration = int(duration)
    user_rate = int(user_rate)
    main_phase = Phase(duration=duration, arrival_rate=user_rate)
    if duration > 120:
        phases = [
            Phase(duration=60, arrival_rate=int(user_rate/4)),
            Phase(duration=60, arrival_rate=int(user_rate/2)),
            main_phase,
        ]
    else:
        phases = [main_phase]

    context = {
        'dtd_path': settings.TSUNG_DTD_PATH,
        'phases': phases,
        'casedb': os.path.join(settings.DB_FILES_DIR, 'casedb-{}.csv'.format(backend_name)),
        'userdb': os.path.join(settings.DB_FILES_DIR, 'userdb-{}.csv'.format(backend_name)),
        'host': backend.settings['HOST'],
        'port': backend.settings['PORT'],
        'submission_url': backend.submission_url,
        'domain': settings.DOMAIN,
        'create_submission': os.path.join(settings.BASEDIR, 'forms', 'create.xml'),
        'update_submission': os.path.join(settings.BASEDIR, 'forms', 'update.xml'),
        'do_auth': backend.settings['SUBMIT_WITH_AUTH']
    }
    filename = 'tsung-hq-test.xml.j2'
    new_filename = os.path.join(settings.BUILD_DIR, filename[:-3])
    with open(new_filename, 'w') as f:
        f.write(_render_template(filename, context))
        print("Built config: {}".format(new_filename))


@task
def load_db(backend_name):
    if not os.path.isdir(settings.DB_FILES_DIR):
        os.makedirs(settings.DB_FILES_DIR)

    backend = _get_backend(backend_name)
    if confirm("Do you want to delete the current database?"):
        backend.check_ssh_access()
        backend.stop()
        backend.reset_db()
        print('Bootstrapping service with domain and superuser')
        backend.bootstrap_service()

        backend.start()
        print('Creating test users')
        users = backend.create_users(settings.NUM_UNIQUE_USERS)

        user_db = os.path.join(settings.DB_FILES_DIR, 'userdb-{}.csv'.format(backend_name))
        with open(user_db, "w") as file:
            for user in users:
                file.write("{},{},{}\n".format(
                    user.id, user.username, user.password
                ))

    backend.load_data(settings.DB_FILES_DIR)


@task
def awesome_test(backend, user_rate, duration, load=False, notes=None):
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
                log_dir = line.split(':')[1].strip()
                log_dir = log_dir.replace('"', '')
    except Exception as e:
        if hasattr(e, 'stderr'):
            print(e.stderr)
        else:
            raise

    if log_dir:
        print("Creating README in log directory")
        context = {
            'notes': notes,
            'settings': get_settings_for_readme(),
            'user_rate': user_rate,
            'duration': duration
        }
        with open(os.path.join(log_dir, 'README.md'), 'w') as f:
            f.write(_render_template('README.md.j2', context))

        print("Generating report")
        title = 'Awesome Test: backend={}, user_rate={}, duration={}'.format(
            backend.name, user_rate, duration
        )
        with cd(log_dir):
            sh.Command('/usr/lib/tsung/bin/tsung_stats.pl')('--title', title)

            print(sh.cat('README.md'))
