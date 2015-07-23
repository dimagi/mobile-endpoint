from __future__ import print_function
import os
import random
import requests
import uuid
from uuid import uuid4
import settings


class Backend(object):
    name = None

    def __init__(self):
        self.submission_url = settings.BACKENDS[self.name]['SUBMISSION_URL'].format(
            domain=settings.DOMAIN,
            hq_app_id=settings.HQ_APP_ID
        )

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
                replace("%%_user_id%%", settings.USER_ID).\
                replace("%%_username%%", settings.USERNAME).\
                replace("%%_form_instance_id%%", uuid4().hex)
            req = requests.post(self.submission_url, files={"xml_submission_file": form}, verify=False)
            req.raise_for_status()

    def populate_case_csv(self, limit, dest):
        raise NotImplementedError


class Current(Backend):
    name = 'current'

    def populate_case_csv(self, limit, dest):
        # Pull random-ish case ids from the database.

        # Erase the contents of the file
        open(dest, 'w').close()

        url = "http://{host}:{port}/commcarehq/_design/cases_by_server_date/_view/by_server_modified_on".format(
            host=settings.BACKENDS[self.name]['COUCH_HOST'],
            port=settings.BACKENDS[self.name]['COUCH_PORT'],
        )

        for i in xrange(limit):
            got_a_doc = False
            while not got_a_doc:
                response = requests.get(url, verify=False, params={
                    "startkey": '["{domain}", "{uuid}"]'.format(
                        domain=settings.DOMAIN,
                        uuid=str(uuid.uuid4()),
                    ),
                    "endkey": '["{domain}", {{}}]'.format(domain=settings.DOMAIN),
                    "reduce": False,
                    "limit": 1,
                })

                try:
                    id = response.json().get("rows", [])[0].get("id")
                except IndexError:
                    id = None

                if id:
                    got_a_doc = True
                    with open(dest, "a") as file:
                        file.write(id + "\n")

        print("Successfully copied {limit} rows to {dest}".format(
            limit=limit,
            dest=dest,
        ))


class Prototype(Backend):
    name = 'prototype'
