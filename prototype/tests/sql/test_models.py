# -*- coding: utf-8 -*-
from datetime import datetime
import hashlib
import random
import string
from uuid import uuid4

import pytest
from mobile_endpoint.backends.manager import get_dao, BACKEND_SQL

from mobile_endpoint.models import db, FormData, Synclog
from mobile_endpoint import shardedmodels
from mobile_endpoint.synclog.checksum import Checksum
from mobile_endpoint.utils import json_format_datetime
from tests.conftest import delete_all_data, rowsize, sql
from tests.utils import create_synclog


@pytest.mark.usefixtures("testapp", "sqldb", "sql_reset")
@sql
class TestModels(object):
    def test_basic(self, testapp):
        form = FormData(id=str(uuid4()), domain='test', received_on=datetime.utcnow(),
                        user_id=str(uuid4()), md5=hashlib.md5('asdf').digest())

        # TODO: reimplement the idea of a relationship (this is a big one)
        # case = CaseData(id=str(uuid4()), domain='test', owner_id=str(uuid4()),
        #                 server_modified_on=datetime.utcnow(), case_json={'a': 'b'})
        # form.cases.append(case)

        with db.session.begin():
            db.session.add(form)

        form = FormData.query.filter_by(domain="test").first()
        assert form is not None
        # cases = form.cases
        # assert len(cases) == 1

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
        case = shardedmodels.CaseData(id=case_id, domain='test', owner_id=str(uuid4()),
                        server_modified_on=datetime.utcnow(), case_json={'a': 'b'})

        case.save()
        assert shardedmodels.CaseData.get_case("test", case_id).version == 0

        # change to simple property updates version
        case.closed = True
        case.save()
        assert shardedmodels.CaseData.get_case("test", case_id).version == 1

        # TODO: reimplement the idea of a relationship (this is a big one)
        # # addition of a form
        # form = FormData(id=str(uuid4()), domain='test', received_on=datetime.utcnow(),
        #                 user_id=str(uuid4()), md5=hashlib.md5('asdf').digest())
        # with db.session.begin():
        #     # TODO: Can't do this anymore
        #     case.forms.append(form)
        # assert shardedmodels.CaseData.get_case("test", case_id).version == 2
        #
        # # addition of an index
        # index = CaseIndex(case_id=case.id, domain=case.domain, identifier='parent', referenced_type='dog')
        # with db.session.begin():
        #     # TODO: Can't do this right now (can probably maintain this relation, but need to figure out how)
        #     case.indices.append(index)
        #
        # assert shardedmodels.CaseData.get_case("test", case_id).version == 3


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
