# -*- coding: utf-8 -*-
from abc import abstractmethod
from uuid import uuid4

from mobile_endpoint.views.response import OPEN_ROSA_SUCCESS_RESPONSE
from tests.mock import CaseFactory, CaseStructure, post_case_blocks, CaseRelationship
from tests.utils import create_synclog

DOMAIN = 'test_domain'


class ReceiverTestMixin(object):
    """
    Mixin for different receiver backends. Override the _assert_form/case/synclog methods
    to test the backend itself.
    """

    @abstractmethod
    def _get_backend(self):
        pass

    @abstractmethod
    def _assert_form(self, form_id, user_id, synclog_id=None):
        pass

    @abstractmethod
    def _assert_case(self, case_id, owner_id, num_forms=1, closed=False, indices=None):
        pass

    @abstractmethod
    def _assert_synclog(self, id, case_ids=None, dependent_ids=None, index_tree=None):
        pass

    def test_vanilla_form(self, testapp, client):
        user_id = str(uuid4())
        form_id = str(uuid4())
        with testapp.app_context():
            result = post_case_blocks(self._get_backend(), client, '', form_extras={
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
            result = post_case_blocks(self._get_backend(), client, '', form_extras={
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
                self._get_backend(),
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
                self._get_backend(),
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
            factory = CaseFactory(self._get_backend(), client, domain=DOMAIN, case_defaults={
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
