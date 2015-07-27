from __future__ import print_function
from collections import namedtuple
import json
from uuid import uuid4
import requests
from requests.auth import HTTPBasicAuth
import sh
from loaders import DataLoader, CouchRowLoader, FormLoaderSQL, FullCaseLoaderSQL, SynclogLoaderSQL
import settings
from utils import get_psql, execute_sql_file, cd

User = namedtuple('User', 'id username password')


class Backend(object):
    name = None

    def __init__(self):
        self.settings = settings.BACKENDS[self.name]

    def load_data(self, scale, dest_folder):
        pass

    def bootstrap_service(self):
        pass

    def create_users(self, user_list):
        pass

    def run_manage_py(self, command, *args):
        python = '{}/bin/python'.format(settings.PYTHONN_ENV)
        manage = '{}/manage.py'.format(settings.HQ_ENVIRONMENT_ROOT)
        try:
            if settings.TEST_SERVER == 'localhost':
                with cd(settings.HQ_ENVIRONMENT_ROOT):
                    sh.Command(python)(manage, command, *args)
            else:
                sh.ssh(settings.TEST_SERVER, '{command} {manage} {command} {args}'.format(
                    command='cd {} && {}'.format(settings.HQ_ENVIRONMENT_ROOT, python),
                    manage=manage,
                    args=' '.join(args)))
        except Exception as e:
            print(e.stderr)



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
        self.submission_url = self.settings['SUBMISSION_URL']
        self.base_url = 'http://{host}:{port}'.format(
            host=self.settings['HOST'],
            port=self.settings['PORT'],
        )

    def reset_db(self):
        print('Dropping postgres', self.settings['PG_DATABASE'])
        sh.dropdb(self.settings['PG_DATABASE'], '--if-exists')
        print('Creating postgres', self.settings['PG_DATABASE'])
        sh.createdb(self.settings['PG_DATABASE'])

        print('Dropping couch', self.couch_url)
        response = requests.delete(self.couch_url, auth=self.auth)
        if response.status_code not in (200, 404):
            raise Exception("Failed to delete couch database: {}\n{}".format(self.couch_url, response.text))

        print('Creating couch', self.couch_url)
        response = requests.put(self.couch_url, auth=self.auth)
        if not response.status_code == 201:
            raise Exception("Failed to create couch database: {}\n{}".format(self.couch_url, response.text))

        print('Running syncdb')
        self.run_manage_py(
            'syncdb',
            '--noinput',
        )

        print('Running migrate')
        self.run_manage_py(
            'migrate',
            '--noinput',
        )


    def load_data(self, scale, dest_folder):
        row_loader = CouchRowLoader(self.couch_url, self.auth)
        loader = DataLoader(scale, row_loader, row_loader, row_loader)
        loader.run()
        loader.save_database(dest_folder)

    def bootstrap_service(self):
        self.run_manage_py(
            'bootstrap',
            settings.DOMAIN,
            self.settings['SUPERUSER_USERNAME'],
            self.settings['SUPERUSER_PASSWORD']
        )

    def create_users(self, number):
        users = []
        for user_id in range(number):
            users.append(self._create_user())

        return users

    def _create_user(self):
        payload = {
            'username': str(uuid4()),
            'password': settings.MOBILE_USER_PASSWORD,
        }
        auth = HTTPBasicAuth(self.settings['SUPERUSER_USERNAME'], self.settings['SUPERUSER_PASSWORD'])
        result = requests.post('{}/a/{}/api/v0.5/user/'.format(
            self.base_url, settings.DOMAIN
        ), data=json.dumps(payload), auth=auth, headers={'Content-Type': 'application/json'})
        assert result.status_code == 201, result.text
        payload['id'] = result.json()['id']
        return User(**payload)


class Prototype(Backend):
    name = 'prototype'

    def __init__(self):
        super(Prototype, self).__init__()

        self.psql = get_psql(self.name)
        self.submission_url = self.settings['SUBMISSION_URL']

    def reset_db(self):
        sh.dropdb(self.settings['PG_DATABASE'], '--if-exists')
        sh.createdb(self.settings['PG_DATABASE'])
        execute_sql_file(self.psql, 'prototype.sql')

    def load_data(self, scale, dest_folder):
        loader = DataLoader(scale, FormLoaderSQL(self.psql), FullCaseLoaderSQL(self.psql), SynclogLoaderSQL(self.psql))
        loader.run()
        loader.save_database(dest_folder)

    def bootstrap_service(self):
        pass

    def create_users(self, number):
        return []
