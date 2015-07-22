from __future__ import print_function
import os
import settings
import uuid
import requests


class RowToCSV(object):
    table = None
    columns = None

    def __init__(self, limit):
        self.limit = limit

    def copy(self):

        # Erase the contents of the file
        open(self.dest, 'w').close()

        url = "http://{host}:{port}/commcarehq/_design/cases_by_server_date/_view/by_server_modified_on".format(
            host=settings.COUCH_HOST,
            port=settings.COUCH_PORT,
        )

        for i in xrange(self.limit):
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
                    with open(self.dest, "a") as file:
                        file.write(id + "\n")

        print("Successfully copied {limit} rows to {dest}".format(
            limit=self.limit,
            dest=self.dest,
        ))


class CaseToCSV(RowToCSV):
    table = 'casedata'
    dest = os.path.join(settings.BASEDIR, 'tsung/files/casedb.csv')
    columns = ['id']


def load_csv(limit):
    cases = CaseToCSV(limit)
    cases.copy()
