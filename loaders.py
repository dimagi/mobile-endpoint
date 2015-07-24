from __future__ import print_function
from Queue import Queue
from abc import ABCMeta, abstractmethod
from copy import copy, deepcopy
from datetime import datetime
import hashlib
import json
import random
from uuid import uuid4
import requests
import settings
from utils import load_json, json_format_datetime


ENABLE_TRIGGERS = "ALTER TABLE {table} ENABLE TRIGGER ALL"

DISABLE_TRIGGERS = "ALTER TABLE {table} DISABLE TRIGGER ALL"


class RowLoader(object):
    __metaclass__ = ABCMeta

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.flush()

    def flush(self):
        pass

    @abstractmethod
    def put_doc(self, doc):
        pass


class SQLRowLoader(RowLoader):
    __metaclass__ = ABCMeta
    table = None
    columns = []

    def __init__(self, psql):
        self.queue = Queue()
        assert self.table, 'missing table name'
        assert self.columns, 'missing columns'
        self.psql = psql

    def __enter__(self):
        sql = "COPY {table} ({columns}) from STDIN CSV QUOTE '\"' ESCAPE E'\\\\';".format(
            table=self.table,
            columns=','.join(self.columns)
        )
        self.command = self.psql(c=sql, _bg=True, _in=self.queue)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.queue.put_nowait(None)
        self.command.wait()

    def put_row(self, columns):
        row = '"{}"\n'.format('","'.join(columns))
        self.queue.put_nowait(row)

    @abstractmethod
    def doc_to_rows(self, doc):
        pass

    def put_doc(self, doc):
        rows = self.doc_to_rows(doc)
        if rows:
            for row in rows:
                self.put_row(row)


class CouchRowLoader(RowLoader):
    def __init__(self, db_url, auth):
        self.db_url = db_url
        self.auth = auth
        self.queue = []

    def flush(self):
        data = json.dumps({
            'docs': self.queue
        })
        result = requests.post('{}/_bulk_docs'.format(self.db_url), auth=self.auth, data=data, headers={
            'content-type': "application/json"
        })
        assert result.status_code == 201, '{},{}'.format(result.status_code, result.text)
        self.queue = []

    def put_doc(self, doc):
        self.queue.append(doc)
        if len(self.queue) > 100:
            self.flush()


class FormLoaderSQL(SQLRowLoader):
    table = 'form_data'
    columns = ['id', 'domain', 'received_on', 'user_id', 'md5', 'synclog_id', 'attachments']

    def doc_to_rows(self, doc):
        return [
            [doc['_id'], doc['domain'], datetime.utcnow().isoformat(),
             doc['form']['meta']['userID'], hashlib.md5(uuid4().hex).hexdigest(), doc['last_sync_token'], '{}']
        ]


class CaseLoaderSQL(SQLRowLoader):
    table = 'case_data'
    columns = ['id', 'domain', 'closed', 'owner_id', 'server_modified_on', 'case_json', 'attachments']

    def doc_to_rows(self, doc):
        case_json = json.dumps(doc)
        case_json = case_json.replace('"', '\\"')
        return [
            [doc['_id'], doc['domain'], 'false', doc['owner_id'], datetime.utcnow().isoformat(), case_json, '{}']
        ]


class CaseFormRelationshipLoaderSQL(SQLRowLoader):
    table = 'case_form'
    columns = ['case_id', 'form_id']

    def doc_to_rows(self, doc):
        for form_id in doc['xform_ids']:
            yield [doc['_id'], form_id]


class CaseIndexLoaderSQL(SQLRowLoader):
    table = 'case_index'
    columns = ['case_id', 'domain', 'identifier', 'referenced_id', 'referenced_type']

    def doc_to_rows(self, doc):
        if 'indices' in doc:
            for index in doc['indices']:
                yield [doc['_id'], doc['domain'], index['identifier'], index['referenced_id'], index['referenced_type']]


class SynclogLoaderSQL(RowLoader):
    table = 'synclog'
    columns = ['id', 'date', 'domain', 'user_id', 'hash', 'owner_ids_on_phone']

    def __init__(self, psql):
        self.psql = psql

    def put_doc(self, doc):
        owner_ids = '{{{}}}'.format(','.join(doc['owner_ids_on_phone']))
        row = [doc['_id'], doc['date'], settings.DOMAIN, doc['user_id'], 'abc', owner_ids]
        quoted_row = "'{}'".format("','".join(row))
        self.psql(c="INSERT INTO synclog ({columns}) VALUES ({values})".format(
            columns=','.join(self.columns),
            values=quoted_row
        ))


class FullCaseLoaderSQL(RowLoader):
    def __init__(self, psql):
        self.psql = psql
        self.case_loader = CaseLoaderSQL(psql)
        self.case_form_relationship_loader = CaseFormRelationshipLoaderSQL(psql)
        self.case_index_loader = CaseIndexLoaderSQL(psql)

        self.tables_with_triggers = [
            self.case_form_relationship_loader.table,
            self.case_index_loader.table
        ]

    def _do_triggers(self, sql_template):
        for table in self.tables_with_triggers:
            self.psql(c=sql_template.format(table=table))

    def pre_load_hook(self):
        self._do_triggers(DISABLE_TRIGGERS)

    def post_load_hook(self):
        self._do_triggers(ENABLE_TRIGGERS)

    def __enter__(self):
        self.pre_load_hook()
        self.case_loader.__enter__()
        self.case_form_relationship_loader.__enter__()
        self.case_index_loader.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.case_index_loader.__exit__(exc_type, exc_val, exc_tb)
        self.case_form_relationship_loader.__exit__(exc_type, exc_val, exc_tb)
        self.case_loader.__exit__(exc_type, exc_val, exc_tb)
        self.post_load_hook()

    def put_doc(self, doc):
        self.case_loader.put_doc(doc)
        self.case_form_relationship_loader.put_doc(doc)
        self.case_index_loader.put_doc(doc)


class DataLoader(object):
    """
    * Load `scale` * settings.SCALE_FACTOR forms.
    * Select settings.FORM_CASE_RATIO forms to also have cases.
    * For settings.NEW_UPDATE_CASE_RATIO of those forms simulate a case update
    * For the rest of the forms load a single case for each form.
    * Make it a child case of an existing case for settings.CHILD_CASE_RATIO of the cases.
    """
    def __init__(self, scale, form_loader, case_loader, sync_token_loader):
        self.scale = scale
        self.form_loader = form_loader
        self.case_loader = case_loader
        self.sync_token_loader = sync_token_loader

        self.domain = settings.DOMAIN

        self.form_json = load_json('form.json')
        self.form_case_partial = load_json('form_case_partial.json')
        self.case_json = load_json('case.json')
        self.synclog_json = load_json('synclog.json')

        self.num_cases = self.scale * settings.SCALE_FACTOR * settings.FORM_CASE_RATIO
        self.case_ids = {}
        self.user_ids = {}
        self.case_forms = {}
        self.user_synclogs = {}

        self.num_case_indexes = 0
        self.num_case_updates = 0

    def print_estimates(self):
        forms = settings.SCALE_FACTOR * self.scale
        case_indexes = int(self.num_cases * settings.CHILD_CASE_RATIO)
        print("Loading data. Estimated numbers:")
        print("  forms:  ", forms)
        print("  cases:  ", self.num_cases)
        print("  case indexes: ", case_indexes)
        print("")

    def print_actual(self):
        forms = settings.SCALE_FACTOR * self.scale
        print("")
        print("Loading complete. Actual numbers:")
        print("  forms:  ", forms)
        print("  cases:  ", len(self.case_ids.keys()))
        print("  case indexes: ", self.num_case_indexes)
        print("  case updates: ", self.num_case_updates)

    @staticmethod
    def _get_doc_id(id_dict, max_num):
        id_index = random.randint(0, max_num)
        new = False
        if id_index not in id_dict:
            id_dict[id_index] = uuid4().hex
            new = True

        return id_dict[id_index], new

    def get_user_id(self):
        user_id, new = self._get_doc_id(self.user_ids, settings.NUM_UNIQUE_USERS)
        if new:
            synclog_id = uuid4().hex
            self.user_synclogs[user_id] = synclog_id

            synclog = deepcopy(self.synclog_json)
            synclog['_id'] = synclog_id
            synclog['user_id'] = user_id
            synclog['owner_ids_on_phone'] = [user_id]
            synclog['date'] = json_format_datetime(datetime.utcnow())
            self.sync_token_loader.put_doc(synclog)
            self.sync_token_loader.flush()

        return user_id, new

    def get_case_id(self):
        return self._get_doc_id(self.case_ids, self.num_cases)

    def get_form(self, form_id, has_case):
        form = deepcopy(self.form_json)
        form['domain'] = self.domain
        form['_id'] = form_id
        user_id = self.get_user_id()[0]
        form['form']['meta']['userID'] = user_id
        form['last_sync_token'] = self.user_synclogs[user_id]

        if has_case:
            case_id, new = self.get_case_id()
            case = copy(self.form_case_partial)
            case['@case_id'] = case_id
            case['date_modified'] = json_format_datetime(datetime.utcnow())
            case['user_id'] = user_id
            if not new:
                self.num_case_updates += 1
                del case['create']
            form['case'] = case

            case_forms = self.case_forms.setdefault(case_id, [])
            case_forms.append(form_id)
        return form

    def get_case(self, case_id, forms, is_child_case):
        case = deepcopy(self.case_json)
        case['_id'] = case_id
        case['domain'] = self.domain
        now = json_format_datetime(datetime.utcnow())
        case['modified_on'] = now
        case['server_modified_on'] = now
        user_id = random.choice(self.user_ids.values())
        case['user_id'] = user_id
        case['owner_id'] = user_id
        case['xform_ids'] = forms

        if is_child_case:
            self.num_case_indexes += 1
            case_ids = self.case_forms.keys()
            parent_id = random.choice(case_ids)
            while parent_id == case_id:
                parent_id = random.choice(case_ids)

            case['indices'] = [{
                "doc_type": "CommCareCaseIndex",
                "identifier": "parent",
                "referenced_type": "registration",
                "referenced_id": parent_id
            }]

        return case

    def run(self):
        self.print_estimates()

        for chunk in range(self.scale):
            print("Loading forms {} to {}".format(chunk * settings.SCALE_FACTOR, (chunk + 1) * settings.SCALE_FACTOR))
            with self.form_loader as loader:
                for i in range(settings.SCALE_FACTOR):
                    has_case = random.random() < settings.FORM_CASE_RATIO
                    form_id = str(uuid4())
                    form = self.get_form(form_id, has_case)
                    loader.put_doc(form)

        print('')
        count = 0
        with self.case_loader as loader:
            for case_id, forms in self.case_forms.items():
                is_child_case = random.random() < settings.CHILD_CASE_RATIO
                case = self.get_case(case_id, forms, is_child_case)
                loader.put_doc(case)
                count += 1
                if count % self.scale == 0:
                    print("Loaded cases {} to {}".format(count - self.scale, count))
        print("Loaded cases {}".format(count))

        self.print_actual()
