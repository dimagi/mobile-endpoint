# -*- coding: utf-8 -*-
from datetime import datetime
import hashlib
from uuid import uuid4

import pytest

from mobile_endpoint.models import db, FormData, CaseData


@pytest.mark.usefixtures("testapp")
class TestModels(object):
    def test_basic(self, testapp):
        form = FormData(id=str(uuid4()), domain='test', received_on=datetime.utcnow(),
                        user_id=str(uuid4()), md5=hashlib.md5('asdf').digest(), form_json={'form': {}})

        case = CaseData(id=str(uuid4()), domain='test', owner_id=str(uuid4()),
                        server_modified_on=datetime.utcnow(), case_json={'a': 'b'})
        form.cases.append(case)

        db.session.add(form)
        db.session.commit()

        form = FormData.query.filter_by(domain="test").first()
        assert form is not None
        cases = form.cases
        assert len(cases) == 1
