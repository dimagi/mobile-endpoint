from __future__ import print_function

import json
import os
import requests
from collections import namedtuple
from requests.auth import HTTPBasicAuth
from uuid import uuid4

import settings

User = namedtuple('User', 'id username password')


class Backend(object):
    tsung_test_template = 'tsung-hq-test.xml.j2'
    transactions_dir = None

    def __init__(self, endpoint_name, config):
        self.endpoint_name = endpoint_name
        self.settings = config
        self.submission_url = self.settings['SUBMISSION_URL'].format(domain=self.settings['DOMAIN'])
        self.restore_url = self.settings['RESTORE_URL'].format(domain=self.settings['DOMAIN'])
        default_port = 443 if self.settings['HTTPS'] else 80
        self.port = self.settings.get('PORT', default_port)
        proto = 'https' if self.settings['HTTPS'] else 'http'
        self.base_url = '{proto}://{host}:{port}'.format(
            proto=proto,
            host=self.settings['HOST'],
            port=self.port,
        )

    def tsung_template_context(self):
        return {
            'dtd_path': settings.TSUNG_DTD_PATH,
            'casedb': os.path.join(settings.DB_FILES_DIR, 'casedb-{}.csv'.format(self.endpoint_name)),
            'userdb': os.path.join(settings.DB_FILES_DIR, 'userdb-{}.csv'.format(self.endpoint_name)),
            'host': self.settings['HOST'],
            'port': self.port,
            'server_type': 'ssl' if self.settings['HTTPS'] else 'tcp',
            'submission_url': '/a/{}/receiver/'.format(self.settings['DOMAIN']),
            'restore_url': '/a/{}/phone/restore/'.format(self.settings['DOMAIN']),
            'sso_auth_url': '/a/{}/api/v0.5/sso/'.format(self.settings['DOMAIN']),
            'domain': self.settings['DOMAIN'],
            'simple_submission': os.path.join(settings.BASEDIR, 'forms', 'nocase.xml'),
            'create_submission': os.path.join(settings.BASEDIR, 'forms', 'create.xml'),
            'update_submission': os.path.join(settings.BASEDIR, 'forms', 'update.xml'),
            'do_auth': self.settings['SUBMIT_WITH_AUTH'],
        }

    def is_running(self):
        try:
            requests.get('{}/'.format(self.base_url))
        except:
            return False
        else:
            return True

    def create_users(self, number):
        users = []
        for i in range(number):
            print('Creating user {} of {}'.format(i, number))
            users.append(self._create_user())

        return users

    def _create_user(self):
        raise NotImplementedError()


class Production(Backend):
    def _create_user(self):
        payload = {
            'username': str(uuid4()),
            'password': settings.MOBILE_USER_PASSWORD,
        }
        auth = HTTPBasicAuth(self.settings['SUPERUSER_USERNAME'], self.settings['SUPERUSER_PASSWORD'])
        result = requests.post('{}/a/{}/api/v0.5/user/'.format(
            self.base_url, self.settings['DOMAIN']
        ), data=json.dumps(payload), auth=auth, headers={'Content-Type': 'application/json'})
        assert result.status_code == 201, json.dumps(result.json(), indent=True)
        payload['id'] = result.json()['id']
        return User(**payload)
