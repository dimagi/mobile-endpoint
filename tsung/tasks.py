import os
import shutil
from collections import namedtuple

import sh
import sys

from datetime import datetime
from invoke import task

import backends
import settings
from utils import cd

Phase = namedtuple('Phase', 'duration, arrival_rate')


def _get_backend(endpoint):
    backend_settings = settings.ENDPOINTS[endpoint]
    backend = backend_settings['BACKEND']
    return {
        'production': backends.Production,
    }[backend](endpoint, backend_settings)


def _render_template(filename, context, searchpath=None):
    from jinja2 import Environment, FileSystemLoader
    searchpath = searchpath or []
    env = Environment(loader=FileSystemLoader([settings.TEMPLATE_DIR] + searchpath))
    template = env.get_template(filename)
    return template.render(**context)


@task
def clean_build():
    if os.path.isdir(settings.BUILD_DIR):
        shutil.rmtree(settings.BUILD_DIR)

@task
def tsung_build(endpoint, test_run):
    if not os.path.isdir(settings.BUILD_DIR):
        os.makedirs(settings.BUILD_DIR)

    backend = _get_backend(endpoint)
    context = backend.tsung_template_context()
    context.update(settings.TEST_RUNS[test_run])

    filename = backend.tsung_test_template
    new_filename = os.path.join(settings.BUILD_DIR, filename[:-3])
    with open(new_filename, 'w') as f:
        f.write(_render_template(filename, context))
        print("Built config: {}".format(new_filename))


@task
def load_users(endpoint, numusers):
    numusers = int(numusers)
    backend = _get_backend(endpoint)
    users = backend.create_users(numusers)
    user_db = os.path.join(settings.DB_FILES_DIR, 'userdb-{}.csv'.format(endpoint))
    with open(user_db, "w") as file:
        for user in users:
            file.write("{},{},{}\n".format(
                user.id, user.username, user.password
            ))

@task
def generate_report(runname, endpoint=None, testrun=None):
    print("Generating report")
    backend_name = 'unknown'
    if endpoint:
        backend_name = _get_backend(endpoint).__class__.__name__

    title = 'Awesome Test: enpoint={}, backend={}, test_run={}'.format(
        endpoint or 'Unknown', backend_name, testrun or 'Unknown'
    )
    log_dir_root = os.path.join(settings.TSUNG_LOG_DIR, runname)
    log_dir = os.walk(log_dir_root).next()[1][0]
    with cd(os.path.join(log_dir_root, log_dir)):
        sh.Command('/usr/lib/tsung/bin/tsung_stats.pl')('--title', title)

@task
def archive_logs(runname):
    log_dir = os.path.join(settings.TSUNG_LOG_DIR, runname)
    path = "{}.tar.gz".format(log_dir)
    print("Creating archive: {}".format(path))
    sh.tar("-czf", path, "--directory={}".format(log_dir), ".")


def create_readme(run_name, notes, testrun):
    print("Creating README in log directory")
    context = {
        'notes': notes,
        'test_run': settings.TEST_RUNS[testrun]
    }
    readme_path = os.path.join(settings.TSUNG_LOG_DIR, run_name, 'README.md')
    with open(readme_path, 'w') as f:
        f.write(_render_template('README.md.j2', context))
    return readme_path

@task
def awesome_test(endpoint, testrun, notes=None):
    tsung_build(endpoint, testrun)

    backend = _get_backend(endpoint)
    if not backend.is_running():
        print("Service is not running!")

    run_name = "tsung_run_{}_{:%Y%m%d-%H%M}".format(endpoint, datetime.utcnow())
    log_dir = os.path.join(settings.TSUNG_LOG_DIR, run_name)
    test_file = "build/{}".format(backend.tsung_test_template[:-3])
    args = ("-l", log_dir, "-f", test_file, "start")
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
        generate_report(run_name, endpoint, testrun)
        readme_path = create_readme(run_name, notes, testrun)
        archive_logs(run_name)
        print("RUN COMPLETE")
        print(sh.cat(readme_path))
