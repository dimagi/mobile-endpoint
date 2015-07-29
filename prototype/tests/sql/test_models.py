# -*- coding: utf-8 -*-
from datetime import datetime
import hashlib
import random
import string
from uuid import uuid4

import pytest

from mobile_endpoint.models import db, FormData, CaseData, Synclog, CaseIndex
from mobile_endpoint.synclog.checksum import Checksum
from mobile_endpoint.utils import json_format_datetime
from tests.conftest import delete_all_data
from tests.utils import create_synclog


@pytest.mark.usefixtures("testapp", "sqldb", "db_reset")
class TestModels(object):
    def test_basic(self, testapp):
        form = FormData(id=str(uuid4()), domain='test', received_on=datetime.utcnow(),
                        user_id=str(uuid4()), md5=hashlib.md5('asdf').digest())

        case = CaseData(id=str(uuid4()), domain='test', owner_id=str(uuid4()),
                        server_modified_on=datetime.utcnow(), case_json={'a': 'b'})
        form.cases.append(case)

        with db.session.begin():
            db.session.add(form)

        form = FormData.query.filter_by(domain="test").first()
        assert form is not None
        cases = form.cases
        assert len(cases) == 1

    def test_synclog(self, testapp):
        id = str(uuid4())
        checksum = Checksum([str(uuid4()) for i in range(10)])
        initial_hash = checksum.hexdigest()
        synclog = Synclog(id=id, date=datetime.utcnow(), user_id=str(uuid4()), domain='test', hash=initial_hash)

        with db.session.begin():
            db.session.add(synclog)

        synclog = Synclog.query.get(synclog.id)
        sync_checksum = synclog.checksum
        assert checksum.hexdigest() == sync_checksum.hexdigest()

    def test_case_versioning(self, testapp):
        case_id = str(uuid4())
        case = CaseData(id=case_id, domain='test', owner_id=str(uuid4()),
                        server_modified_on=datetime.utcnow(), case_json={'a': 'b'})

        with db.session.begin():
            db.session.add(case)
        assert CaseData.query.get(case_id).version == 0

        # change to simple property updates version
        with db.session.begin():
            case.closed = True
        assert CaseData.query.get(case_id).version == 1

        # addition of a form
        form = FormData(id=str(uuid4()), domain='test', received_on=datetime.utcnow(),
                        user_id=str(uuid4()), md5=hashlib.md5('asdf').digest())
        with db.session.begin():
            case.forms.append(form)
        assert CaseData.query.get(case_id).version == 2

        # addition of an index
        index = CaseIndex(case_id=case.id, domain=case.domain, identifier='parent', referenced_type='dog')
        with db.session.begin():
            case.indices.append(index)

        assert CaseData.query.get(case_id).version == 3


@pytest.mark.usefixtures("testapp", "sqldb")
class TestDetermineRowSizes(object):
    @pytest.mark.skipif(True, reason="Not a real test. Only run this manually")
    def test_table_size_form(self):
        """
        Insert 10000 rows into the form_data table. Run scripts/get_table_sizes.sh to
        output the resulting DB size.
        """
        # Config that varies the row size
        attachments_per_row = 0
        domain = 'test-domain'

        num_rows = 10000

        delete_all_data()
        synclog_id = create_synclog(domain, str(uuid4()))
        forms = []
        for i in range(num_rows):
            attachments = _get_attachment_json(attachments_per_row)
            forms.append(
                FormData(id=str(uuid4()), domain=domain, received_on=datetime.utcnow(),
                        user_id=str(uuid4()), md5=hashlib.md5(str(uuid4())).digest(), synclog_id=synclog_id,
                        attachments=attachments or None)
            )

        db.session.bulk_save_objects(forms)

    @pytest.mark.skipif(True, reason="Not a real test. Only run this manually")
    def test_table_size_case(self):
        """
        Insert 10000 rows into the form_data table. Run scripts/get_table_sizes.sh to
        output the resulting DB size.
        """
        # Config that varies the row size
        case_properties_per_row = 75
        forms_per_case = 10
        attachments_per_row = 1
        domain = 'test-domain'

        num_rows = 10000

        delete_all_data()
        cases = []
        for i in range(num_rows):
            attachments = _get_attachment_json(attachments_per_row)
            case_json = case_json_compact(case_properties_per_row, forms_per_case)
            cases.append(
                CaseData(id=str(uuid4()), domain=domain, owner_id=str(uuid4()),
                        server_modified_on=datetime.utcnow(),
                        case_json=case_json,
                        attachments=attachments or None)
            )

        db.session.bulk_save_objects(cases)


def _get_attachment_json(num):
    return {
        _random_string(20): {
            'mime': _random_string(20),
            'size': 5000,
        }
        for i in range(num)
    }


def case_json_expanded(num_props, num_forms):
    """
    {
        'property_name': {
            'form_id': 'ID of the form that last touched this property',
            'value': 'property value',
            'date': 'date of last update'
        },
        ...
    }
    """
    form_ids = [str(uuid4()) for i in range(num_forms)]
    case_json = {
        _random_string(20): {
            'form_id': random.choice(form_ids)[0],
            'value': _random_string(20),
            'date': json_format_datetime(datetime.utcnow())
        }
        for i in range(num_props)
    }
    return case_json


def case_json_compact(num_props, num_forms):
    """The goal of the compact format is to reduce the overall size of the JSON
    by removing duplicated data. Mostly this is form IDs and form dates.

    Compact format look like this:
    {
        'f': {
            'unique_form_id_prefix': [form_id, form_date]
            ...
        },
        'p': {
            'property_name': [form_id_prefix, value]
            ...
        }
    }

    The 'unique_form_id_prefix' is as many characters as are needed from the front of the form_id
    in order to make it unique in the 'f' dict.
    """
    form_ids = [str(uuid4()) for i in range(num_forms)]
    f_dict = {}
    for form_id in form_ids:
        prefix = form_id[0]
        while prefix in f_dict:
            prefix = form_id[:len(prefix) + 1]

        f_dict[prefix] = [form_id, json_format_datetime(datetime.utcnow())]

    case_json = {
        'f': f_dict,
        'p': {
            _random_string(20): [random.choice(f_dict.keys()), _random_string(20)]
            for i in range(num_props)
        }
    }
    return case_json


def _random_string(length):
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))
