from __future__ import print_function
import os
import settings

from utils import psql, execute_query


class RowToCSV(object):
    table = None
    columns = None

    def __init__(self, limit=10):
        self.limit = limit

    def copy(self):
        sql = "\COPY (SELECT {columns} FROM {table} ORDER BY random() LIMIT {limit}) TO '{dest}' WITH CSV".format(
            table=self.table,
            columns=','.join(self.columns),
            dest=self.dest,
            limit=self.limit,
        )
        cmd = psql(c=sql, _bg=True)
        if cmd.stderr:
            print(cmd.stderr)
        else:
            print(cmd.stdout)
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
