# -*- coding: utf-8 -*-
from uuid import uuid4

import pytest

from mobile_endpoint.models import FormData, CaseData, Synclog
from mobile_endpoint.synclog.checksum import Checksum
from mobile_endpoint.views.response import OPEN_ROSA_SUCCESS_RESPONSE
from tests.mock import CaseFactory, CaseStructure, post_case_blocks, CaseRelationship
from tests.utils import create_synclog

DOMAIN = 'test_domain'


@pytest.mark.usefixtures("testapp", "client", "db_reset")
class TestReceiver(object):

    def _assert_form(self, form_id, user_id, synclog_id=None):
        sql_form = FormData.query.get(form_id)
        assert sql_form is not None
        assert sql_form.domain == DOMAIN
        assert sql_form.user_id == user_id
        if synclog_id:
            assert sql_form.synclog_id == synclog_id
        else:
            assert sql_form.synclog_id is None

    def _assert_case(self, case_id, owner_id, num_forms=1, closed=False, indices=None):
        sql_case = CaseData.query.get(case_id)
        assert sql_case is not None
        assert sql_case.domain == DOMAIN
        assert sql_case.closed == closed
        assert len(sql_case.forms) == num_forms
        assert sql_case.owner_id == owner_id

        if indices:
            sql_indices = {}
            for index in sql_case.indices:
                sql_indices[index.identifier] = {
                    'referenced_type': index.referenced_type,
                    'referenced_id': index.referenced_id
                }

            assert sql_indices == indices

        return sql_case

    def _assert_synclog(self, id, case_ids=None, dependent_ids=None, index_tree=None):
        synclog = Synclog.query.get(id)
        case_ids = case_ids or []
        dependent_ids = dependent_ids or []
        index_tree = index_tree or {}
        assert case_ids == synclog.case_ids_on_phone
        assert dependent_ids == synclog.dependent_case_ids_on_phone
        assert index_tree == synclog.index_tree
        assert Checksum(case_ids).hexdigest() == synclog.hash

    def test_vanilla_form(self, testapp, client):
        user_id = str(uuid4())
        form_id = str(uuid4())
        with testapp.app_context():
            result = post_case_blocks(client, '', form_extras={
                    'form_id': form_id,
                    'user_id': user_id,
                    'domain': DOMAIN,
                })

        assert result.status_code == 201
        assert result.data == OPEN_ROSA_SUCCESS_RESPONSE.xml()

        self._assert_form(form_id, user_id)

    def test_form_with_synclog(self, testapp, client):
        user_id = str(uuid4())
        form_id = str(uuid4())
        synclog_id = create_synclog(DOMAIN, user_id)
        with testapp.app_context():
            result = post_case_blocks(client, '', form_extras={
                    'form_id': form_id,
                    'user_id': user_id,
                    'domain': DOMAIN,
                    'headers': {
                        'last_sync_token': synclog_id
                    }
                })

        assert result.status_code == 201
        assert result.data == OPEN_ROSA_SUCCESS_RESPONSE.xml()

        self._assert_form(form_id, user_id, synclog_id)

    def test_create_case(self, testapp, client):
        user_id = str(uuid4())
        form_id = str(uuid4())
        case_id = str(uuid4())
        synclog_id = create_synclog(DOMAIN, user_id)
        with testapp.app_context():
            factory = CaseFactory(
                client,
                domain=DOMAIN,
                case_defaults={
                    'user_id': user_id,
                    'owner_id': user_id,
                    'case_type': 'duck',
                    'update': {'identity': 'mallard'}
                },
                form_extras={
                    'headers': {
                        'last_sync_token': synclog_id
                    }
                }
            )
            factory.create_or_update_cases([
                CaseStructure(case_id, attrs={'create': True}),
            ], form_extras={
                'form_id': form_id,
                'user_id': user_id,
            })

        self._assert_form(form_id, user_id, synclog_id)
        self._assert_case(case_id, user_id)
        self._assert_synclog(synclog_id, case_ids=[case_id])

    def test_update_case(self, testapp, client):
        user_id = str(uuid4())
        case_id = str(uuid4())
        synclog_id = create_synclog(DOMAIN, user_id)
        with testapp.app_context():
            factory = CaseFactory(
                client,
                domain=DOMAIN,
                case_defaults={
                    'user_id': user_id,
                    'owner_id': user_id,
                    'case_type': 'duck',
                },
                form_extras={
                    'headers': {
                        'last_sync_token': synclog_id
                    }
                }
            )
            factory.create_or_update_cases([
                CaseStructure(case_id, attrs={'create': True}),
            ])

            self._assert_case(case_id, user_id)
            self._assert_synclog(synclog_id, case_ids=[case_id])

            updated_case, = factory.create_or_update_case(
                CaseStructure(case_id, attrs={'update': {'identity': 'mallard'}, 'close': True})
            )

            assert updated_case.identity == 'mallard'
            assert updated_case.closed is True
            self._assert_case(case_id, user_id, num_forms=2, closed=True)
            self._assert_synclog(synclog_id, case_ids=[])

    def test_case_index(self, testapp, client):
        user_id = str(uuid4())
        owner_id = str(uuid4())
        with testapp.app_context():
            factory = CaseFactory(client, domain=DOMAIN, case_defaults={
                'user_id': user_id,
                'owner_id': owner_id,
                'case_type': 'duck',
            })
            child, parent = factory.create_or_update_case(
                CaseStructure(
                    attrs={'create': True, 'case_type': 'duckling'},
                    relationships=[
                        CaseRelationship(
                            CaseStructure(attrs={'case_type': 'duck'})
                        ),
                    ])
            )

            self._assert_case(parent.id, owner_id)
            self._assert_case(child.id, owner_id, indices={
                'parent': {
                    'referenced_type': 'duck',
                    'referenced_id': parent.id,
                }
            })
