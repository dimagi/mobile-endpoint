# -*- coding: utf-8 -*-
import base64
from datetime import datetime
import re
from uuid import uuid4, UUID
import os

import pytest

from mobile_endpoint.models import FormData, CaseData, Synclog, db
from mobile_endpoint.restore.restore import User
from mobile_endpoint.synclog.checksum import Checksum
from mobile_endpoint.views.response import OPEN_ROSA_SUCCESS_RESPONSE
from tests.dummy import dummy_user, dummy_restore_xml
from tests.mock import CaseFactory, CaseStructure, post_case_blocks, CaseRelationship
from tests.utils import check_xml_line_by_line

DOMAIN = 'test_domain'


@pytest.mark.usefixtures("testapp", "client")
class TestRestore(object):
    def test_user_restore(self, testapp, client):
        assert 0 == len(Synclog.query.all())

        user = dummy_user(str(uuid4()))
        restore_payload = generate_restore_response(client, DOMAIN, user)

        synclogs = Synclog.query.all()
        assert len(synclogs) == 1
        synclog = synclogs[0]
        check_xml_line_by_line(
            dummy_restore_xml(user, synclog.id, items=3),
            restore_payload,
        )


def generate_restore_response(client, domain, user):
    headers = {'Authorization': 'Basic ' + base64.b64encode('{}:{}'.format(user.username, user.password))}
    result = client.get(
        'ota/restore/{domain}?version=2.0&items=true&user_id={user_id}'.format(
            domain=domain,
            user_id=user.user_id),
        headers=headers
    )
    assert result.status_code == 200
    return result.data

    
def _create_synclog(user_id, owner_ids=None, case_ids=None, dependent_case_ids=None, index_tree=None):
    case_ids = case_ids or []
    hash = Checksum(case_ids).hexdigest()
    synclog_id = str(uuid4())
    db.session.add(Synclog(
        id=synclog_id,
        date=datetime.utcnow(),
        domain=DOMAIN,
        user_id=user_id,
        hash=hash,
        owner_ids_on_phone=owner_ids or [user_id],
        case_ids_on_phone=case_ids,
        dependent_case_ids_on_phone=dependent_case_ids or [],
        index_tree=index_tree or {}
    ))
    db.session.commit()
    return synclog_id
