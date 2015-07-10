# -*- coding: utf-8 -*-
import re
from uuid import uuid4, UUID
import os

import pytest

from mobile_endpoint.models import FormData, CaseData
from mobile_endpoint.views.response import OPEN_ROSA_SUCCESS_RESPONSE
from tests.mock import CaseFactory, CaseStructure, post_case_blocks, CaseRelationship

DOMAIN = 'test_domain'


@pytest.mark.usefixtures("testapp", "client")
class TestApi(object):
    def _assert_form(self, form_id, user_id):
        sql_form = FormData.query.get(form_id)
        assert sql_form is not None
        assert sql_form.domain == DOMAIN
        assert UUID(sql_form.user_id) == UUID(user_id)

    def _assert_case(self, case_id, owner_id, closed=False, indices=None):
        sql_case = CaseData.query.get(case_id)
        assert sql_case is not None
        assert sql_case.domain == DOMAIN
        assert sql_case.closed == closed
        assert len(sql_case.forms) == 1
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
        assert case_ids == synclog.case_ids_on_phone


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

    def test_create_case(self, testapp, client):
        user_id = uuid4().hex
        owner_id = uuid4().hex
        form_id = uuid4().hex
        case_id = uuid4().hex
        with testapp.app_context():
            factory = CaseFactory(client, domain=DOMAIN, case_defaults={
                'user_id': user_id,
                'owner_id': owner_id,
                'case_type': 'duck',
                'update': {'identity': 'mallard'}
            })
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
        owner_id = str(uuid4())
        case_id = str(uuid4())
        with testapp.app_context():
            factory = CaseFactory(client, domain=DOMAIN, case_defaults={
                'user_id': user_id,
                'owner_id': owner_id,
                'case_type': 'duck',
            })
            factory.create_or_update_cases([
                CaseStructure(case_id, attrs={'create': True}),
            ])

            self._assert_case(case_id, owner_id)

            updated_case, = factory.create_or_update_case(
                CaseStructure(case_id, attrs={'update': {'identity': 'mallard'}})
            )

            assert updated_case.identity == 'mallard'
            assert len(CaseData.query.get(case_id).forms) == 2

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
                    'referenced_id': UUID(parent.id),
                }
            })
