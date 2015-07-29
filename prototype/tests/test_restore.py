# -*- coding: utf-8 -*-
import base64
from uuid import uuid4

import pytest
import time
from mobile_endpoint.case import const
from mobile_endpoint.case.xml import V2

from mobile_endpoint.models import Synclog
from mobile_endpoint.restore import xml
from tests.dummy import dummy_user, dummy_restore_xml
from tests.mock import CaseFactory, CaseStructure
from tests.utils import check_xml_line_by_line

DOMAIN = 'test_domain'


@pytest.mark.usefixtures("testapp", "client", "sqldb", "db_reset")
class TestRestore(object):
    user_id = str(uuid4())
    case_id = str(uuid4())

    def test_user_restore(self, testapp, client):
        assert 0 == len(Synclog.query.all())

        user = dummy_user(self.user_id)
        restore_payload = generate_restore_response(client, DOMAIN, user)

        synclogs = Synclog.query.all()
        assert len(synclogs) == 1
        synclog = synclogs[0]
        check_xml_line_by_line(
            dummy_restore_xml(user, synclog.id, items=3),
            restore_payload,
        )

    def test_user_restore_with_case(self, testapp, client):
        with testapp.app_context():
            factory = CaseFactory(
                client,
                domain=DOMAIN,
                case_defaults={
                    'user_id': self.user_id,
                    'owner_id': self.user_id,
                    'case_type': 'duck',
                }
            )
            new_case, = factory.create_or_update_case(
                CaseStructure(self.case_id, attrs={
                    'create': True,
                    'case_name': 'Fish',
                    'update': {'last_name': 'Mooney'}})
            )

        user = dummy_user(self.user_id)
        restore_payload = generate_restore_response(client, DOMAIN, user)

        synclog = Synclog.query.one()

        case_xml = xml.get_case_xml(
            new_case, [
                const.CASE_ACTION_CREATE,
                const.CASE_ACTION_UPDATE],
            version=V2)

        check_xml_line_by_line(
            dummy_restore_xml(user, synclog.id, case_xml=case_xml, items=4),
            restore_payload,
        )

    def test_sync_token(self, testapp, client):
        """
        Tests sync token / sync mode support
        """
        self.test_user_restore_with_case(testapp, client)
        user = dummy_user(self.user_id)

        synclog = Synclog.query.one()
        synclog_id = synclog.id

        restore_payload = generate_restore_response(client, DOMAIN, user, since=synclog_id)
        new_synclog = Synclog.query.filter(Synclog.previous_log_id == synclog_id).one()
        new_synclog_id = new_synclog.id

        # should no longer have a case block in the restore XML
        check_xml_line_by_line(
            dummy_restore_xml(user, new_synclog_id, items=3),
            restore_payload,
        )

        time.sleep(1)  # current jsonobject doesn't support microseconds in datetime fields
        # update the case
        with testapp.app_context():
            factory = CaseFactory(
                client,
                domain=DOMAIN,
                case_defaults={
                    'user_id': str(uuid4()),
                    'owner_id': self.user_id,
                    'case_type': 'duck',
                }
            )
            updated_case, = factory.create_or_update_case(
                CaseStructure(self.case_id, attrs={'update': {'occupation': 'restaurant owner'}}),
            )

        new_restore_payload = generate_restore_response(client, DOMAIN, user, since=new_synclog_id)

        new_new_synclog = Synclog.query.filter(Synclog.previous_log_id == new_synclog_id).one()

        case_xml = xml.get_case_xml(updated_case, [const.CASE_ACTION_UPDATE], version=V2)
        # case block should come back
        check_xml_line_by_line(
            dummy_restore_xml(user, new_new_synclog.id, case_xml=case_xml, items=4),
            new_restore_payload,
        )


def generate_restore_response(client, domain, user, since=None):
    headers = {'Authorization': 'Basic ' + base64.b64encode('{}:{}'.format(user.username, user.password))}
    result = client.get(
        'ota/restore/{domain}?version=2.0&items=true&user_id={user_id}{since}'.format(
            domain=domain,
            user_id=user.user_id,
            since='&since={}'.format(since) if since else ''),
        headers=headers
    )
    assert result.status_code == 200
    return result.data
