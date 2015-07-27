from __future__ import print_function
import requests
from requests.auth import HTTPBasicAuth
import sh
from loaders import DataLoader, CouchRowLoader, FormLoaderSQL, FullCaseLoaderSQL, SynclogLoaderSQL
import settings
from utils import get_psql, execute_sql_file


class Backend(object):
    name = None

    def __init__(self):
        self.settings = settings.BACKENDS[self.name]

    def load_data(self, scale, dest_folder):
        pass


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

    def reset_db(self):
        response = requests.delete(self.couch_url, auth=self.auth)
        if response.status_code not in (200, 404):
            raise Exception("Failed to delete couch database: {}\n{}".format(self.couch_url, response.text))

        response = requests.put(self.couch_url, auth=self.auth)
        if not response.status_code == 201:
            raise Exception("Failed to create couch database: {}\n{}".format(self.couch_url, response.text))

    def load_data(self, scale, dest_folder):
        row_loader = CouchRowLoader(self.couch_url, self.auth)
        loader = DataLoader(scale, row_loader, row_loader, row_loader)
        loader.run()
        loader.save_database(dest_folder)


class Prototype(Backend):
    name = 'prototype'

    def __init__(self):
        super(Prototype, self).__init__()

        self.psql = get_psql(self.name)
        self.submission_url = '/'.join([self.settings['SUBMISSION_URL'], settings.DOMAIN])

    def reset_db(self):
        sh.dropdb(self.settings['PG_DATABASE'], '--if-exists')
        sh.createdb(self.settings['PG_DATABASE'])
        execute_sql_file(self.psql, 'prototype.sql')

    def load_data(self, scale, dest_folder):
        loader = DataLoader(scale, FormLoaderSQL(self.psql), FullCaseLoaderSQL(self.psql), SynclogLoaderSQL(self.psql))
        loader.run()
        loader.save_database(dest_folder)
