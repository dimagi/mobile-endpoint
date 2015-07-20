# -*- coding: utf-8 -*-
from datetime import datetime
import hashlib
from uuid import uuid4

import pytest

from mobile_endpoint.models import db, FormData, CaseData, Synclog, CaseIndex
from mobile_endpoint.synclog.checksum import Checksum


@pytest.mark.usefixtures("testapp")
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
