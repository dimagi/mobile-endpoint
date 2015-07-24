from __future__ import print_function
import os
import random
import requests
import uuid
from uuid import uuid4
from requests.auth import HTTPBasicAuth
import sh
from loaders import DataLoader, CouchRowLoader, FormLoaderSQL, FullCaseLoaderSQL, SynclogLoaderSQL
import settings
from utils import get_psql, execute_sql_file


class Backend(object):
    name = None

    def __init__(self):
        self.settings = settings.BACKENDS[self.name]

    def load_data(self, scale):
        """
        * Load `scale` * settings.SCALE_FACTOR forms.
        * Select settings.FORM_CASE_RATIO forms to also have cases.
        * For settings.NEW_UPDATE_CASE_RATIO of those forms simulate a case update
        * For the rest of the forms load a single case for each form.
        * Make it a child case of an existing case for settings.CHILD_CASE_RATIO of the cases.
        """
        # TODO: Make this fast by implementing backend specific versions.

        requests.packages.urllib3.disable_warnings()
        scale_factor = settings.SCALE_FACTOR

        with open(os.path.join(settings.BASEDIR, 'forms', 'create.xml')) as f:
            create_case_form = f.read()
        with open(os.path.join(settings.BASEDIR, 'forms', 'nocase.xml')) as f:
            no_case_form = f.read()

        for i in xrange(scale * scale_factor):
            # TODO: Make requests in parallel
            has_case = random.random() < settings.FORM_CASE_RATIO
            if has_case:
                form = create_case_form
            else:
                form = no_case_form
            form = form.replace("%%_case_id%%", uuid4().hex).\
                replace("%%_user_id%%", self.settings['USER_ID']).\
                replace("%%_username%%", self.settings['USERNAME']).\
                replace("%%_form_instance_id%%", uuid4().hex)
            req = requests.post(self.settings['SUBMISSION_URL'], files={"xml_submission_file": form}, verify=False)
            req.raise_for_status()

    def populate_case_csv(self, limit, dest):
        raise NotImplementedError


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

    def reset_db(self):
        response = requests.delete(self.couch_url, auth=self.auth)
        if response.status_code not in (200, 404):
            raise Exception("Failed to delete couch database: {}\n{}".format(self.couch_url, response.text))

        response = requests.put(self.couch_url, auth=self.auth)
        if not response.status_code == 201:
            raise Exception("Failed to create couch database: {}\n{}".format(self.couch_url, response.text))

    def load_data(self, scale):
        row_loader = CouchRowLoader(self.couch_url, self.auth)
        loader = DataLoader(scale, row_loader, row_loader, row_loader)
        loader.run()

    def populate_case_csv(self, limit, dest):
        # Pull random-ish case ids from the database.

        # Erase the contents of the file
        open(dest, 'w').close()

        url = '{}/_design/cases_by_server_date/_view/by_server_modified_on'.format(self.couch_url)

        chunksize = 10
        got = 0
        while got != limit:
            response = requests.get(url, verify=False, params={
                "startkey": '["{domain}", "{uuid}"]'.format(
                    domain=settings.DOMAIN,
                    uuid=str(uuid.uuid4()),
                ),
                "endkey": '["{domain}", {{}}]'.format(domain=settings.DOMAIN),
                "reduce": False,
                "limit": chunksize,
            })

            rows = response.json().get("rows", [])
            with open(dest, "a") as file:
                for row in rows:
                    file.write(row.get("id") + "\n")
                    got += 1

        print("Successfully copied {limit} rows to {dest}".format(
            limit=limit,
            dest=dest,
        ))


class Prototype(Backend):
    name = 'prototype'

    def __init__(self):
        super(Prototype, self).__init__()

        self.psql = get_psql(self.name)

    def reset_db(self):
        sh.dropdb(self.settings['PG_DATABASE'], '--if-exists')
        sh.createdb(self.settings['PG_DATABASE'])
        execute_sql_file(self.psql, 'prototype.sql')

    def load_data(self, scale):

        loader = DataLoader(scale, FormLoaderSQL(self.psql), FullCaseLoaderSQL(self.psql), SynclogLoaderSQL(self.psql))
        loader.run()

    def populate_case_csv(self, limit, dest):

        # Erase the contents of the file
        open(dest, 'w').close()

        LOWEST_UUID = "00000000-0000-0000-0000-000000000000"
        KEEP = 3

        chunksize = 10
        got = 0
        while got != limit:
            high_uuid = str(uuid.uuid4())
            low_uuid = high_uuid[:KEEP] + LOWEST_UUID[KEEP:]
            sql = ("\COPY (SELECT {columns} FROM {table} WHERE id BETWEEN '{low_uuid}' and '{high_uuid}' "
                   "ORDER BY id DESC LIMIT {limit}) TO stdout WITH CSV").format(
                table='case_data',
                columns=','.join(['id']),
                low_uuid=low_uuid,
                high_uuid=high_uuid,
                limit=chunksize
            )
            cmd = self.psql(c=sql)
            if cmd.stderr:
                print(cmd.stderr)
                break
            else:
                if cmd.stdout:
                    with open(dest, "a") as file:
                        file.write(cmd.stdout)
                    got += len(cmd.stdout.split('\n'))
                    if got % 100 == 0:
                        print("Copied {} of {} rows.".format(got, limit))

        print("Successfully copied {limit} rows to {dest}".format(
            limit=limit,
            dest=dest,
        ))
