from __future__ import print_function
from Queue import Queue
from collections import namedtuple
from datetime import datetime
import random
from uuid import uuid4
import sys
import settings
from utils import psql, load_json_escaped, confirm


ENABLE_TRIGGERS = "ALTER TABLE {table} ENABLE TRIGGER ALL"

DISABLE_TRIGGERS = "ALTER TABLE {table} DISABLE TRIGGER ALL"


class RowLoader(object):
    table = None
    columns = []

    def __init__(self):
        self.queue = Queue()
        assert self.table, 'missing table name'
        assert self.columns, 'missing columns'

    def __enter__(self):
        sql = "COPY {table} ({columns}) from STDIN CSV;".format(
            table=self.table,
            columns=','.join(self.columns)
        )
        self.command = psql(c=sql, _bg=True, _in=self.queue)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.queue.put_nowait(None)
        self.command.wait()

    def put_row(self, columns):
        row = '"{}"\n'.format('","'.join(columns))
        self.queue.put_nowait(row)


class FormLoader(RowLoader):
    table = 'formdata'
    columns = ['id', 'domain', 'received_on', 'user_id', 'form_json']


class CaseLoader(RowLoader):
    table = 'casedata'
    columns = ['id', 'domain', 'closed', 'owner_id', 'server_modified_on', 'case_json']


class CaseFormRelationshipLoader(RowLoader):
    table = 'case_form'
    columns = ['case_id', 'form_id']


class CaseIndexLoader(RowLoader):
    table = 'caseindex'
    columns = ['case_id', 'referenced_id']
    
    
class FullCaseLoader(object):
    def __init__(self):
        self.case_loader = CaseLoader()
        self.case_form_relationship_loader = CaseFormRelationshipLoader()
        self.case_index_loader = CaseIndexLoader()

        self.tables_with_triggers = [
            self.case_form_relationship_loader.table,
            self.case_index_loader.table
        ]

    def _do_triggers(self, sql_template):
        for table in self.tables_with_triggers:
            psql(c=sql_template.format(table=table))

    def disable_triggers(self):
        self._do_triggers(DISABLE_TRIGGERS)

    def enable_triggers(self):
        self._do_triggers(ENABLE_TRIGGERS)

    def __enter__(self):
        self.disable_triggers()
        self.case_loader.__enter__()
        self.case_form_relationship_loader.__enter__()
        self.case_index_loader.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.case_index_loader.__exit__(exc_type, exc_val, exc_tb)
        self.case_form_relationship_loader.__exit__(exc_type, exc_val, exc_tb)
        self.case_loader.__exit__(exc_type, exc_val, exc_tb)
        self.enable_triggers()

    def put_case(self, form_id, case_columns, parent_id=None):
        case_id = case_columns[0]
        self.case_loader.put_row(case_columns)
        self.case_form_relationship_loader.put_row([case_id, form_id])
        if parent_id:
            self.case_index_loader.put_row([case_id, parent_id])

    def update_case(self, form_id, case_id):
        self.case_form_relationship_loader.put_row([case_id, form_id])



FormWithCase = namedtuple('FormWithCase', 'form_id domain')

def load_data(scale):
    """
    * Load `scale` * settings.SCALE_FACTOR forms.
    * Select settings.FORM_CASE_RATIO forms to also have cases.
    * For settings.NEW_UPDATE_CASE_RATIO of those forms simulate a case update
    * For the rest of the forms load a single case for each form.
    * Make it a child case of an existing case for settings.CHILD_CASE_RATIO of the cases.
    """
    form_json = load_json_escaped('form.json')
    case_json = load_json_escaped('case.json')
    scale_factor = settings.SCALE_FACTOR

    for chunk in range(scale):
        print("Loading {} to {}".format(chunk * scale_factor, (chunk + 1) * scale_factor))
        case_forms = []
        with FormLoader() as loader:
            for i in range(scale_factor):
                has_case = random.random() < settings.FORM_CASE_RATIO
                form_id = uuid4().hex
                domain = settings.DOMAIN
                if has_case:
                    case_forms.append(FormWithCase(form_id=form_id, domain=domain))
                columns = [form_id, domain, datetime.utcnow().isoformat(), uuid4().hex, form_json]
                loader.put_row(columns)

        case_ids = []
        with FullCaseLoader() as loader:
            for form_with_case in case_forms:
                is_update = random.random() < settings.NEW_UPDATE_CASE_RATIO
                if is_update and case_ids:
                    case_id = random.choice(case_ids)
                    loader.update_case(form_with_case.form_id, case_id)
                else:
                    is_child_case = random.random() < settings.CHILD_CASE_RATIO
                    case_id = uuid4().hex
                    parent_id = None
                    if is_child_case and case_ids:
                        parent_id = random.choice(case_ids)

                    case_ids.append(case_id)

                    columns = [case_id, form_with_case.domain, 'FALSE', uuid4().hex, datetime.utcnow().isoformat(), case_json]
                    loader.put_case(form_with_case.form_id, columns, parent_id)
