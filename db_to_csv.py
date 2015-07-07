from __future__ import print_function
import os
import settings
import uuid

from utils import psql, execute_query


class RowToCSV(object):
    table = None
    columns = None

    def __init__(self, limit=10):
        self.limit = limit

    def copy(self):

        # Erase the contents of the file
        open(self.dest, 'w').close()

        LOWEST_UUID = "00000000-0000-0000-0000-000000000000"
        KEEP = 3

        for i in xrange(self.limit):
            got_a_row = False
            while not got_a_row:
                high_uuid = str(uuid.uuid4())
                low_uuid = high_uuid[:KEEP] + LOWEST_UUID[KEEP:]
                sql = "\COPY (SELECT {columns} FROM {table} WHERE id BETWEEN '{low_uuid}' and '{high_uuid}' ORDER BY id DESC LIMIT 1) TO stdout WITH (FORMAT TEXT, DELIMITER ',')".format(
                    table=self.table,
                    columns=','.join(self.columns),
                    low_uuid=low_uuid,
                    high_uuid=high_uuid,
                )
                cmd = psql(c=sql)
                if cmd.stderr:
                    print(cmd.stderr)
                    break
                else:
                    if cmd.stdout:
                        with open(self.dest, "a") as file:
                            file.write(cmd.stdout)
                        got_a_row = True
                        if i+1 % 100 == 0:
                            print("Copied {} of {} rows.".format(i, self.limit))

        print("Successfully copied {limit} rows to {dest}".format(
            limit=self.limit,
            dest=self.dest,
        ))


class FormToCSV(RowToCSV):
    table = 'formdata'
    dest = os.path.join(settings.BASEDIR, 'tsung/files/formdb.csv')
    columns = ['id', 'domain', 'form_json']


class CaseToCSV(RowToCSV):
    table = 'casedata'
    dest = os.path.join(settings.BASEDIR, 'tsung/files/casedb.csv')
    columns = ['id', 'case_json']


def load_csv(limit):
    forms = FormToCSV(limit)
    forms.copy()

    cases = CaseToCSV(limit)
    cases.copy()
