# -*- coding: utf-8 -*-
from datetime import datetime
import hashlib
from uuid import uuid4

import pytest

from mobile_endpoint.models import db, FormData, CaseData, Synclog
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
