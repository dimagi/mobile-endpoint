from __future__ import print_function
from collections import namedtuple
import json
import os
from uuid import uuid4
from couchdbkit import push, Database, CouchdbResource
from pymongo import MongoClient

import requests
from requests.auth import HTTPBasicAuth
import sh
import time

from loaders import DataLoader, CouchRowLoader, FormLoaderSQL, FullCaseLoaderSQL, SynclogLoaderSQL, \
    MongoFormLoader, MongoCaseLoader, MongoSynclogLoader
import settings
from utils import get_psql, cd


User = namedtuple('User', 'id username password')


class Backend(object):
    name = None
    tsung_test_template = 'tsung-hq-test.xml.j2'
    transactions_dir = None
    settings_key = None

    def __init__(self):
        settings_key = self.settings_key or self.anme
        self.settings = settings.BACKENDS[settings_key]
        self.psql = get_psql(settings_key)
        self.submission_url = self.settings['SUBMISSION_URL'].format(domain=settings.DOMAIN)

    def tsung_template_context(self, phases):
        return {
            'dtd_path': settings.TSUNG_DTD_PATH,
            'phases': phases,
            'casedb': os.path.join(settings.DB_FILES_DIR, 'casedb-{}.csv'.format(self.name)),
            'userdb': os.path.join(settings.DB_FILES_DIR, 'userdb-{}.csv'.format(self.name)),
            'host': self.settings['HOST'],
            'port': self.settings['PORT'],
            'submission_url': self.submission_url,
            'domain': settings.DOMAIN,
            'create_submission': os.path.join(settings.BASEDIR, 'forms', 'create.xml'),
            'update_submission': os.path.join(settings.BASEDIR, 'forms', 'update.xml'),
            'do_auth': self.settings['SUBMIT_WITH_AUTH']
        }

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
                sh.ssh(settings.TEST_SERVER, '{ssh_command} {manage} {manage_command} {args}'.format(
                    ssh_command='cd {} && {}'.format(self.settings['ENVIRONMENT_ROOT'], python),
                    manage=manage,
                    manage_command=command,
                    args=' '.join(args)), _iter=True)
        except Exception as e:
            if hasattr(e, 'stderr'):
                print(e.stderr)
            raise

    def reset_db(self):
        common_args = ['-h', settings.PG_HOST, '-U', settings.PG_USERNAME]
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
        loader = DataLoader(dest_folder, self.name, row_loader, row_loader, row_loader)
        loader.run()

    def bootstrap_service(self):
        self._run_manage_py(
            'bootstrap',
            settings.DOMAIN,
            self.settings['SUPERUSER_USERNAME'],
            self.settings['SUPERUSER_PASSWORD']
        )

        if not self.settings['SUBMIT_WITH_AUTH']:
            print("Turning off secure submissions for domain")
            params = {'reduce': 'false', 'include_docs': 'true', 'key': '"{}"'.format(settings.DOMAIN)}
            resp = requests.get('{}/_design/domain/_view/domains'.format(
                self.couch_url), params=params, auth=self.auth
            )
            assert resp.status_code == 200, resp.text
            domain = resp.json()['rows'][0]['doc']
            domain['secure_submissions'] = False
            resp = requests.put('{}/{}'.format(self.couch_url, domain['_id']), auth=self.auth, data=json.dumps(domain), headers={
                'content-type': "application/json"
            })
            assert resp.status_code == 201, [resp.status_code, resp.text]

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

    def reset_db(self):
        super(PrototypeSQL, self).reset_db()

        print('Running db upgrade')
        self._run_manage_py(
            'db',
            'upgrade',
        )

    def load_data(self, dest_folder):
        loader = DataLoader(dest_folder, self.name, FormLoaderSQL(self.psql), FullCaseLoaderSQL(self.psql), SynclogLoaderSQL(self.psql))
        loader.run()

    def _create_user(self):
        return User(id=str(uuid4()), username='admin', password='secret')


class PrototypeMongo(Backend):
    name = 'prototype-mongo'

    def _create_user(self):
        return User(id=str(uuid4()), username='admin', password='secret')

    def reset_db(self):
        super(PrototypeMongo, self).reset_db()

        print('Dropping mongo')
        client = MongoClient(settings.BACKENDS[self.name]['MONGO_URI'])
        db = client.get_default_database()
        client.drop_database(db)

        # Mongo dbs are created automatically on first use, so no need to explicitly create one now.
        print('Running mongo db sync')
        self._run_manage_py('syncmongo')

        # The mongo backend uses sql for some things, like OwnershipCleanlinessFlags
        print('Running db upgrade')
        self._run_manage_py('db', 'upgrade',)

    def load_data(self, dest_folder):
        loader = DataLoader(
            dest_folder,
            self.name,
            MongoFormLoader(self.name),
            MongoCaseLoader(self.name),
            MongoSynclogLoader(self.name)
        )
        loader.run()


class PrototypeCouch(Backend):
    name = 'prototype-couch'

    def __init__(self):
        super(PrototypeCouch, self).__init__()
        self.auth = HTTPBasicAuth(self.settings['COUCH_USERNAME'], self.settings['COUCH_PASSWORD'])

        # from mobile_endpoint import create_app
        # app = create_app()
        # dbs = app.config.get('COUCH_DBS')
        # TODO: Grab these from the prototype configuration
        self.dbs = {
            'forms': 'mobile_endpoint_forms',
            'cases': 'mobile_endpoint_cases',
            'synclogs': 'mobile_endpoint_synclogs',
        }

    def _get_couch_url(self, db, credentials=False):
        creds = ""
        if credentials:
            creds = "{}:{}@".format(self.settings['COUCH_USERNAME'], self.settings['COUCH_PASSWORD'])
        return "http://{creds}{host}:{port}/{db}".format(
            creds=creds,
            host=self.settings['COUCH_HOST'],
            port=self.settings['COUCH_PORT'],
            db=db,
        )

    def _create_user(self):
        return User(id=str(uuid4()), username='admin', password='secret')

    def reset_db(self):
        super(PrototypeCouch, self).reset_db()

        for db in self.dbs.values():
            url = self._get_couch_url(db)
            print('Dropping couch', url)
            response = requests.delete(url, auth=self.auth)
            if response.status_code not in (200, 404):
                raise Exception("Failed to delete couch database: {}\n{}".format(url, response.text))

        for db in self.dbs.values():
            url = self._get_couch_url(db)
            print('Creating couch', url)
            response = requests.put(url, auth=self.auth)
            if not response.status_code == 201:
                raise Exception("Failed to create couch database: {}\n{}".format(url, response.text))

        # create views
        # This is hacky and I hate it
        design_dir = os.path.join( os.path.dirname(__file__), '..', 'prototype', 'mobile_endpoint', 'backends', 'couch', '_designs',)
        for app_name in os.listdir(design_dir):
            folder = os.path.join(design_dir, app_name)
            push(folder, Database(self._get_couch_url(self.dbs[app_name], credentials=True)), force=True, docid='_design/{}'.format(app_name))

        # The couch backend uses sql for some things, like OwnershipCleanlinessFlags
        print('Running db upgrade')
        self._run_manage_py('db', 'upgrade')

    def load_data(self, dest_folder):
        loader = DataLoader(
            dest_folder,
            self.name,
            CouchRowLoader(self._get_couch_url(self.dbs.get('forms')), self.auth),
            CouchRowLoader(self._get_couch_url(self.dbs.get('cases')), self.auth),
            CouchRowLoader(self._get_couch_url(self.dbs.get('synclogs')), self.auth),
        )
        loader.run()


class RawSQL(PrototypeSQL):
    name = 'raw-sql'
    tsung_test_template = 'tsung-raw-sql.xml.j2'
    transactions_dir = 'postgres'
    settings_key = 'prototype-sql'

    def tsung_template_context(self, phases):
        context = super(RawSQL, self).tsung_template_context(phases)
        context.update({
            'transactions_dir': os.path.join(settings.BUILD_DIR, settings.RAW_TRANSACTION_DIR_NAME, self.transactions_dir),
            'session_type': 'ts_pgsql',
            'host': settings.PG_HOST,
            'port': settings.PG_PORT,
            'pg_database': self.settings['PG_DATABASE'],
            'pg_username': settings.PG_USERNAME,
            'pg_password': settings.PG_PASSWORD,
        })
        return context

class RawCouch(PrototypeCouch):
    tsung_test_template = 'tsung-raw-couch.xml.j2'
    transactions_dir = 'couch'
    name = 'raw-couch'
    settings_key = 'prototype-couch'

    def tsung_template_context(self, phases):
        context = super(RawCouch, self).tsung_template_context(phases)
        context.update({
            'transactions_dir': os.path.join(settings.BUILD_DIR, settings.RAW_TRANSACTION_DIR_NAME, self.transactions_dir),
            'session_type': 'ts_http',
            'host': self.settings['COUCH_HOST'],
            'port': self.settings['COUCH_PORT'],
            'pg_database': self.settings['PG_DATABASE'],
            'pg_username': settings.PG_USERNAME,
            'pg_password': settings.PG_PASSWORD,
            'couch_form_db': self.dbs['forms'],
            'couch_case_db': self.dbs['cases'],
        })
        return context
