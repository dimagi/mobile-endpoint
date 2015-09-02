from __future__ import print_function
from Queue import Queue
from abc import ABCMeta, abstractmethod
from copy import copy, deepcopy
from datetime import datetime
import dateutil.parser
import hashlib
import json
import os
import random
from uuid import uuid4, UUID
from pymongo import MongoClient

import requests

import settings
from utils import load_json, json_format_datetime, update_progress


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
        return []

    def put_doc(self, doc):
        rows = self.doc_to_rows(doc)
        if rows:
            for row in rows:
                self.put_row(row)


class CouchRowLoader(RowLoader):
    def __init__(self, db_url, auth, views_to_update=None):
        self.db_url = db_url
        self.auth = auth
        self.queue = []
        self.views_to_update = []
        if views_to_update:
            for view in views_to_update:
                design, view = view.split('/')
                self.views_to_update.append('_design/{}/_view/{}'.format(design, view))

    def flush(self):
        data = json.dumps({
            'docs': self.queue
        })
        result = requests.post('{}/_bulk_docs'.format(self.db_url), auth=self.auth, data=data, headers={
            'content-type': "application/json"
        })
        assert result.status_code == 201, '{},{}'.format(result.status_code, result.text)
        self.queue = []
        if self.views_to_update:
            self.update_views()

    def update_views(self):
        params = {'reduce': 'false', 'limit': '1'}
        for view in self.views_to_update:
            result = requests.get('{}/{}'.format(self.db_url, view), params, auth=self.auth)
            assert result.status_code == 200, '{}: {},{}'.format(view, result.status_code, result.text)

    def put_doc(self, doc):
        self.queue.append(doc)
        if len(self.queue) > 100:
            self.flush()


class MongoDocLoader(RowLoader):
    collection = None

    def __init__(self, backend):
        self.queue = []
        self.client = MongoClient(settings.BACKENDS[backend]['MONGO_URI'])

    def __exit__(self, exc_type, exc_val, exc_tb):
        super(MongoDocLoader, self).__exit__(exc_type, exc_val, exc_tb)
        self.client.close()

    def put_doc(self, doc):
        self.queue.append(self.doc_to_mongo(doc))
        if len(self.queue) > 100:
            self.flush()

    def flush(self):
        collection = self.client.get_default_database()[self.collection]
        if self.queue:
            collection.insert_many(self.queue)
        self.queue = []

    def doc_to_mongo(self, doc):
        raise NotImplementedError


class MongoFormLoader(MongoDocLoader):
    collection = 'forms'

    def doc_to_mongo(self, doc):
        return {
            '_id': UUID(doc['_id']),
            'domain': doc['domain'],
            'received_on': dateutil.parser.parse(doc['received_on']),
            'user_id': UUID(doc['form']['meta']['userID']),
            'md5': 'wat',
            'synclog_id': UUID(doc['last_sync_token'])
        }


class MongoCaseLoader(MongoDocLoader):
    collection = 'cases'

    def doc_to_mongo(self, doc):
        doc['_id'] = UUID(doc['_id'])
        doc['owner_id'] = UUID(doc['owner_id'])
        doc['server_modified_on'] = dateutil.parser.parse(doc['server_modified_on'])
        doc['indices'] = [
            {
                'identifier': i['identifier'],
                'referenced_type': i['referenced_type'],
                'referenced_id': UUID(i['referenced_id']),
            }
            for i in doc['indices']
        ]
        return doc


class MongoSynclogLoader(MongoDocLoader):
    collection = 'synclogs'

    def doc_to_mongo(self, doc):
        return {
            '_id': UUID(doc['_id']),
            'date': dateutil.parser.parse(doc['date']),
            'user_id': UUID(doc['user_id']),
            'previous_log_id': UUID(doc['previous_log_id']) if doc['previous_log_id'] else None,
            'owner_ids_on_phone': [UUID(i) for i in doc['owner_ids_on_phone']],
            'domain': settings.DOMAIN,
        }
        # NOTE: Doesn't save cases_on_phone or dependent_cases_on_phone


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
    * Loads the user_ids from the userdb.csv file
    * For each user create CASES_PER_USER cases
    """
    def __init__(self, files_folder, backend_name, form_loader, case_loader, sync_token_loader):
        self.case_db_path = os.path.join(files_folder, 'casedb-{}.csv'.format(backend_name))
        self.user_db_path = os.path.join(files_folder, 'userdb-{}.csv'.format(backend_name))

        self.form_loader = form_loader
        self.case_loader = case_loader
        self.sync_token_loader = sync_token_loader

        self.domain = settings.DOMAIN

        self.form_json = load_json('form.json')
        self.form_case_partial = load_json('form_case_partial.json')
        self.case_json = load_json('case.json')
        self.case_update_partial = load_json('case_update_partial.json')
        self.case_index_partial = load_json('case_index_partial.json')
        self.synclog_json = load_json('synclog.json')

        self.user_ids = []  # list of user IDs
        self.selected_case_ids = []  # case_ids to save to the casedb.csv file

        # these get cleared after each user's data has been created
        self.case_ids_gen = []  # list of case ID for current user
        self.case_forms = {}  # list of forms that have updated each case for current user

        self.num_forms = 0
        self.num_cases = 0
        self.num_case_indexes = 0
        self.num_case_updates = 0

        self._load_user_ids()
        self.num_users = len(self.user_ids)

    def _load_user_ids(self):
        with open(self.user_db_path) as f:
            user_data = f.readlines()

        self.user_ids = [
            user.split(',')[0]
            for user in user_data
        ]

    def print_actual(self):
        print("")
        print("Loading complete. Actual numbers:")
        print("  forms:  ", self.num_forms)
        print("  cases:  ", self.num_cases)
        print("  case indexes: ", self.num_case_indexes)
        print("  case updates: ", self.num_case_updates)

    def get_synclog_id(self, user_id):
        synclog_id = str(uuid4())

        synclog = deepcopy(self.synclog_json)
        synclog['_id'] = synclog_id
        synclog['user_id'] = user_id
        synclog['owner_ids_on_phone'] = [user_id]
        synclog['date'] = json_format_datetime(datetime.utcnow())
        self.sync_token_loader.put_doc(synclog)
        self.sync_token_loader.flush()

        return synclog_id

    def get_case_id(self, new):
        if new:
            case_id = str(uuid4())
            self.case_ids_gen.append(case_id)
        else:
            case_id = random.choice(self.case_ids_gen)

        return case_id

    def get_form(self, user_id, synclog_id, create_case):
        form_id = str(uuid4())

        form = deepcopy(self.form_json)
        form['domain'] = self.domain
        form['_id'] = form_id
        form['form']['meta']['userID'] = user_id
        form['last_sync_token'] = synclog_id

        case_id = self.get_case_id(create_case)
        case = copy(self.form_case_partial)
        case['@case_id'] = case_id
        case['date_modified'] = json_format_datetime(datetime.utcnow())
        case['user_id'] = user_id
        if not create_case:
            self.num_case_updates += 1
            del case['create']

        form['case'] = case

        case_forms = self.case_forms.setdefault(case_id, [])
        case_forms.append(form_id)
        return form

    def get_case(self, user_id, case_id, forms, is_child_case):
        case = deepcopy(self.case_json)
        case['_id'] = case_id
        case['domain'] = self.domain
        now = json_format_datetime(datetime.utcnow())
        case['modified_on'] = now
        case['server_modified_on'] = now
        case['user_id'] = user_id
        case['owner_id'] = user_id
        case['xform_ids'] = forms
        case['actions'][0]['xform_id'] = forms[0]
        case['actions'][0]['user_id'] = user_id

        for form_id in forms[1:]:
            action = deepcopy(self.case_update_partial)
            action['xform_id'] = form_id
            action['user_id'] = user_id
            case['actions'].append(action)

        if is_child_case:
            self.num_case_indexes += 1
            case_ids = self.case_forms.keys()
            parent_id = random.choice(case_ids)
            while parent_id == case_id:
                parent_id = random.choice(case_ids)

            index = {"doc_type": "CommCareCaseIndex", "identifier": "parent",
                     "referenced_type": "registration", "referenced_id": parent_id}
            action = deepcopy(self.case_index_partial)
            action['xform_id'] = forms[-1]
            action['user_id'] = user_id
            action['indices'] = [index]
            case['actions'].append(action)
            case['indices'] = [index]

        return case

    def run(self):
        open(self.case_db_path, 'w').close()

        forms_per_user = float(settings.CASES_PER_USER * settings.FORMS_PER_CASE)

        for i, user_id in enumerate(self.user_ids):
            print('\n\n## Loading data for user {} of {}'.format(i, self.num_users))
            synclog_id = self.get_synclog_id(user_id)
            num_cases_user = 0
            num_forms_user = 0
            with self.form_loader as loader:
                while num_forms_user < forms_per_user:
                    create_case = num_cases_user < settings.CASES_PER_USER
                    form = self.get_form(user_id, synclog_id, create_case)
                    loader.put_doc(form)
                    num_forms_user += 1
                    if create_case:
                        num_cases_user += 1

                    update_progress('Forms:', num_forms_user / forms_per_user)

            self.num_forms += num_forms_user
            self.num_cases += num_cases_user

            print('')
            with self.case_loader as loader:
                case_ids = self.case_forms.keys()
                num_cases = float(len(case_ids))
                for j, case_id in enumerate(case_ids):
                    is_child_case = random.random() < settings.CHILD_CASE_RATIO
                    forms = self.case_forms[case_id]
                    case = self.get_case(user_id, case_id, forms, is_child_case)
                    loader.put_doc(case)
                    update_progress('Cases:', (j + 1) / num_cases)

            self.save_database_and_clear()

        self.print_actual()

    def save_database_and_clear(self):
        export_case_ids_per_user = int(settings.NUM_CASES_TO_UPDATE / self.num_users)

        case_ids = list(self.case_forms.keys())
        random.shuffle(case_ids)
        case_selection = case_ids[:export_case_ids_per_user]

        with open(self.case_db_path, "a") as file:
            file.write("\n".join(case_selection))
            file.write("\n")

        self.case_ids_gen = []
        self.case_forms.clear()
