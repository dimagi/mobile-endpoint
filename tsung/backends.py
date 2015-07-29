from __future__ import print_function
from collections import namedtuple
import json
from uuid import uuid4

import requests
from requests.auth import HTTPBasicAuth
import sh
import time

from loaders import DataLoader, CouchRowLoader, FormLoaderSQL, FullCaseLoaderSQL, SynclogLoaderSQL
import settings
from utils import get_psql, cd


User = namedtuple('User', 'id username password')


class Backend(object):
    name = None

    def __init__(self):
        self.settings = settings.BACKENDS[self.name]
        self.psql = get_psql(self.name)

    def check_ssh_access(self):
        if settings.TEST_SERVER != 'localhost':
            sh.ssh(settings.TEST_SERVER, 'echo ping!')

    def is_running(self):
        try:
            requests.get('http://{}:{}/'.format(self.settings['HOST'], self.settings['PORT']))
        except:
            return False
        else:
            return True

    def _run_manage_py(self, command, *args, **kwargs):
        python = '{}/bin/python'.format(self.settings['PYTHON_ENV'])
        manage = '{}/manage.py'.format(self.settings['ENVIRONMENT_ROOT'])
        try:
            if settings.TEST_SERVER == 'localhost':
                with cd(self.settings['ENVIRONMENT_ROOT']):
                    sh.Command(python)(manage, command, _bg=kwargs.get('bg', False), *args)
            else:
                for line in sh.ssh(settings.TEST_SERVER, '{ssh_command} {manage} {manage_command} {args}'.format(
                    ssh_command='cd {} && {}'.format(self.settings['ENVIRONMENT_ROOT'], python),
                    manage=manage,
                    manage_command=command,
                    args=' '.join(args)), _iter=True):
                    print("    ", line)
        except Exception as e:
            if hasattr(e, 'stderr'):
                print(e.stderr)
            raise

    def reset_db(self):
        common_args = ['-h', self.settings['PG_HOST'], '-U', self.settings['PG_USERNAME']]
        print('Dropping postgres', self.settings['PG_DATABASE'])
        sh.dropdb(self.settings['PG_DATABASE'], *common_args, _ok_code=[0, 1])
        print('Creating postgres', self.settings['PG_DATABASE'])
        sh.createdb(self.settings['PG_DATABASE'], *common_args)

        # verify DB is accessible
        self.psql(c="SELECT 1")

    def start(self):
        print('Starting service: ', self.name)
        if settings.TEST_SERVER == 'localhost':
            self._run_manage_py('runserver', bg=True)
        else:
            sh.ssh(settings.TEST_SERVER, 'sudo supervisorctl start all')

        for i in range(5):
            time.sleep(1)
            if self.is_running():
                return

        raise Exception("Service not running after 5 seconds")

    def stop(self):
        print('Stopping service: ', self.name)
        if settings.TEST_SERVER == 'localhost':
            pids = sh.pgrep('-f', 'manage.py runserver', _ok_code=[0, 1])
            for pid in pids:
                sh.kill(pid.rstrip())
        else:
            sh.ssh(settings.TEST_SERVER, 'sudo supervisorctl stop all')

    def restart(self):
        self.stop()
        self.start()

    def load_data(self, dest_folder):
        raise NotImplementedError()

    def bootstrap_service(self):
        pass

    def create_users(self, number):
        users = []
        for i in range(number):
            print('Creating user {} of {}'.format(i, number))
            users.append(self._create_user())

        return users

    def _create_user(self):
        raise NotImplementedError()


class Current(Backend):
    name = 'current'

    def __init__(self):
        super(Current, self).__init__()
        self.couch_url = "http://{host}:{port}/{db}".format(
            host=self.settings['COUCH_HOST'],
            port=self.settings['COUCH_PORT'],
            db=self.settings['COUCH_DATABASE'],
        )
        self.auth = HTTPBasicAuth(self.settings['COUCH_USERNAME'], self.settings['COUCH_PASSWORD'])
        self.user_ids = []
        self.case_ids = []
        self.submission_url = self.settings['SUBMISSION_URL'].format(domain=settings.DOMAIN)
        self.base_url = 'http://{host}:{port}'.format(
            host=self.settings['HOST'],
            port=self.settings['PORT'],
        )

    def reset_db(self):
        super(Current, self).reset_db()

        print('Dropping couch', self.couch_url)
        response = requests.delete(self.couch_url, auth=self.auth)
        if response.status_code not in (200, 404):
            raise Exception("Failed to delete couch database: {}\n{}".format(self.couch_url, response.text))

        print('Creating couch', self.couch_url)
        response = requests.put(self.couch_url, auth=self.auth)
        if not response.status_code == 201:
            raise Exception("Failed to create couch database: {}\n{}".format(self.couch_url, response.text))

        print('Running syncdb')
        self._run_manage_py(
            'syncdb',
            '--noinput',
        )

        print('Running migrate')
        self._run_manage_py(
            'migrate',
            '--noinput',
        )

    def load_data(self, dest_folder):
        row_loader = CouchRowLoader(self.couch_url, self.auth)
        loader = DataLoader(dest_folder, row_loader, row_loader, row_loader)
        loader.run()

    def bootstrap_service(self):
        self._run_manage_py(
            'bootstrap',
            settings.DOMAIN,
            self.settings['SUPERUSER_USERNAME'],
            self.settings['SUPERUSER_PASSWORD']
        )

    def _create_user(self):
        payload = {
            'username': str(uuid4()),
            'password': settings.MOBILE_USER_PASSWORD,
        }
        auth = HTTPBasicAuth(self.settings['SUPERUSER_USERNAME'], self.settings['SUPERUSER_PASSWORD'])
        result = requests.post('{}/a/{}/api/v0.5/user/'.format(
            self.base_url, settings.DOMAIN
        ), data=json.dumps(payload), auth=auth, headers={'Content-Type': 'application/json'})
        assert result.status_code == 201, json.dumps(result.json(), indent=True)
        payload['id'] = result.json()['id']
        return User(**payload)


class PrototypeSQL(Backend):
    name = 'prototype-sql'

    def __init__(self):
        super(PrototypeSQL, self).__init__()

        self.submission_url = self.settings['SUBMISSION_URL']

    def reset_db(self):
        super(PrototypeSQL, self).reset_db()

        print('Running db upgrade')
        self._run_manage_py(
            'db',
            'upgrade',
        )

    def load_data(self, dest_folder):
        loader = DataLoader(dest_folder, FormLoaderSQL(self.psql), FullCaseLoaderSQL(self.psql), SynclogLoaderSQL(self.psql))
        loader.run()

    def _create_user(self):
        return User(id=str(uuid4()), username='admin', password='secret')
