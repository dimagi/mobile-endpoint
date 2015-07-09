from collections import namedtuple, defaultdict
from copy import copy
import json
from jsonobject.api import JsonObject
from jsonobject.properties import DateTimeProperty, StringProperty, IntegerProperty, ListProperty, DictProperty, \
    SetProperty, ObjectProperty
import logging
from mobile_endpoint.case import const
from mobile_endpoint.synclog.checksum import CaseStateHash, Checksum

logger = logging.getLogger(__name__)


class SyncLogAssertionError(AssertionError):

    def __init__(self, case_id, *args, **kwargs):
        self.case_id = case_id
        super(SyncLogAssertionError, self).__init__(*args, **kwargs)


class AbstractSyncLog(JsonObject):
    date = DateTimeProperty()
    # domain = StringProperty()
    user_id = StringProperty()
    previous_log_id = StringProperty()  # previous sync log, forming a chain
    duration = IntegerProperty()        # in seconds
    log_format = StringProperty()

    # owner_ids_on_phone stores the ids the phone thinks it's the owner of.
    # This typically includes the user id,
    # as well as all groups that that user is a member of.
    owner_ids_on_phone = ListProperty(unicode)

    strict = True  # for asserts

    def _assert(self, conditional, msg="", case_id=None):
        if not conditional:
            if self.strict:
                raise SyncLogAssertionError(case_id, msg)
            else:
                logger.warn("assertion failed: %s" % msg)
                self.has_assert_errors = True

    @classmethod
    def wrap(cls, data):
        ret = super(AbstractSyncLog, cls).wrap(data)
        if hasattr(ret, 'has_assert_errors'):
            ret.strict = False
        return ret

    def phone_is_holding_case(self, case_id):
        raise NotImplementedError()

    def get_footprint_of_cases_on_phone(self):
        """
        Gets the phone's flat list of all case ids on the phone,
        owned or not owned but relevant.
        """
        raise NotImplementedError()

    def get_state_hash(self):
        return CaseStateHash(Checksum(self.get_footprint_of_cases_on_phone()).hexdigest())

    def update_phone_lists(self, xform, case_list):
        """
        Given a form an list of touched cases, update this sync log to reflect the updated
        state on the phone.
        """
        raise NotImplementedError()

    def get_payload_attachment_name(self, version):
        return 'restore_payload_{version}.xml'.format(version=version)

    def has_cached_payload(self, version):
        return self.get_payload_attachment_name(version) in self._doc.get('_attachments', {})

    # anything prefixed with 'tests_only' is only used in tests
    def tests_only_get_cases_on_phone(self):
        raise NotImplementedError()

    def test_only_clear_cases_on_phone(self):
        raise NotImplementedError()


PruneResult = namedtuple('PruneResult', ['seen', 'pruned'])


class IndexTree(JsonObject):
    """
    Document type representing a case dependency tree (which is flattened to a single dict)
    """
    # a flat mapping of cases to lists of cases that they depend on
    indices = DictProperty()

    def __repr__(self):
        return json.dumps(self.indices, indent=2)

    def get_cases_that_directly_depend_on_case(self, case_id, cached_map=None):
        cached_map = cached_map or _reverse_index_map(self.indices)
        return cached_map.get(case_id, [])

    def get_all_cases_that_depend_on_case(self, case_id, cached_map=None):
        """
        Recursively builds a tree of all cases that depend on this case and returns
        a flat set of case ids.

        Allows passing in a cached map of reverse index references if you know you are going
        to call it more than once in a row to avoid rebuilding that.
        """
        def _recursive_call(case_id, all_cases, cached_map):
            all_cases.add(case_id)
            for dependent_case in self.get_cases_that_directly_depend_on_case(case_id, cached_map=cached_map):
                if dependent_case not in all_cases:
                    all_cases.add(dependent_case)
                    _recursive_call(dependent_case, all_cases, cached_map)

        all_cases = set()
        cached_map = cached_map or _reverse_index_map(self.indices)
        _recursive_call(case_id, all_cases, cached_map)
        return all_cases

    def delete_index(self, from_case_id, index_name):
        prior_ids = self.indices.pop(from_case_id, {})
        prior_ids.pop(index_name, None)
        if prior_ids:
            self.indices[from_case_id] = prior_ids

    def set_index(self, from_case_id, index_name, to_case_id):
        prior_ids = self.indices.get(from_case_id, {})
        prior_ids[index_name] = to_case_id
        self.indices[from_case_id] = prior_ids

    def apply_updates(self, other_tree):
        """
        Apply updates from another IndexTree and return a copy with those applied.

        If an id is found in the new one, use that id's indices, otherwise, use this ones,
        (defaulting to nothing).
        """
        assert isinstance(other_tree, IndexTree)
        new = IndexTree(
            indices=copy(self.indices),
        )
        new.indices.update(other_tree.indices)
        return new


def _reverse_index_map(index_map):
    reverse_indices = defaultdict(set)
    for case_id, indices in index_map.items():
        for indexed_case_id in indices.values():
            reverse_indices[indexed_case_id].add(case_id)
    return dict(reverse_indices)


class SimplifiedSyncLog(AbstractSyncLog):
    """
    New, simplified sync log class that is used by ownership cleanliness restore.

    Just maintains a flat list of case IDs on the phone rather than the case/dependent state
    lists from the SyncLog class.
    """
    # log_format = StringProperty(default=LOG_FORMAT_SIMPLIFIED)
    case_ids_on_phone = SetProperty(unicode)
    # this is a subset of case_ids_on_phone used to flag that a case is only around because it has dependencies
    # this allows us to prune it if possible from other actions
    dependent_case_ids_on_phone = SetProperty(unicode)
    owner_ids_on_phone = SetProperty(unicode)
    index_tree = ObjectProperty(IndexTree)

    def save(self, *args, **kwargs):
        # force doc type to SyncLog to avoid changing the couch view.
        self.doc_type = "SyncLog"
        super(SimplifiedSyncLog, self).save(*args, **kwargs)

    def phone_is_holding_case(self, case_id):
        """
        Whether the phone currently has a case, according to this sync log
        """
        return case_id in self.case_ids_on_phone

    def get_footprint_of_cases_on_phone(self):
        return list(self.case_ids_on_phone)

    def prune_case(self, case_id):
        """
        Prunes a case from the tree while also pruning any dependencies as a result of this pruning.
        """
        logger.debug('pruning: {}'.format(case_id))
        self.dependent_case_ids_on_phone.add(case_id)
        reverse_index_map = _reverse_index_map(self.index_tree.indices)
        dependencies = self.index_tree.get_all_cases_that_depend_on_case(case_id, cached_map=reverse_index_map)
        # we can only potentially remove a case if it's already in dependent case ids
        # and therefore not directly owned
        candidates_to_remove = dependencies & self.dependent_case_ids_on_phone
        dependencies_not_to_remove = dependencies - self.dependent_case_ids_on_phone

        def _remove_case(to_remove):
            # uses closures for assertions
            logger.debug('removing: {}'.format(case_id))
            assert to_remove in self.dependent_case_ids_on_phone
            indices = self.index_tree.indices.pop(to_remove, {})
            if to_remove != case_id:
                # if the case had indexes they better also be in our removal list (except for ourselves)
                for index in indices.values():
                    assert index in candidates_to_remove, \
                        "expected {} in {} but wasn't".format(index, candidates_to_remove)
            self.case_ids_on_phone.remove(to_remove)
            self.dependent_case_ids_on_phone.remove(to_remove)

        if not dependencies_not_to_remove:
            # this case's entire relevancy chain is in dependent cases
            # this means they can all now be removed.
            this_case_indices = self.index_tree.indices.get(case_id, {})
            for to_remove in candidates_to_remove:
                _remove_case(to_remove)

            for this_case_index in this_case_indices.values():
                if (this_case_index in self.dependent_case_ids_on_phone and
                        this_case_index not in candidates_to_remove):
                    self.prune_case(this_case_index)
        else:
            # we have some possible candidates for removal. we should check each of them.
            candidates_to_remove.remove(case_id)  # except ourself
            for candidate in candidates_to_remove:
                candidate_dependencies = self.index_tree.get_all_cases_that_depend_on_case(
                    candidate, cached_map=reverse_index_map
                )
                if not candidate_dependencies - self.dependent_case_ids_on_phone:
                    _remove_case(candidate)

    def _add_primary_case(self, case_id):
        self.case_ids_on_phone.add(case_id)
        if case_id in self.dependent_case_ids_on_phone:
            self.dependent_case_ids_on_phone.remove(case_id)

    def update_phone_lists(self, xform, case_list):
        made_changes = False
        logger.debug('syncing {}'.format(self.user_id))
        logger.debug('case ids before update: {}'.format(', '.join(self.case_ids_on_phone)))
        logger.debug('dependent case ids before update: {}'.format(', '.join(self.dependent_case_ids_on_phone)))
        for case in case_list:
            actions = case.get_actions_for_form(xform.get_id)
            for action in actions:
                logger.debug('{}: {}'.format(case._id, action.action_type))
                owner_id = action.updated_known_properties.get("owner_id")
                phone_owns_case = not owner_id or owner_id in self.owner_ids_on_phone

                if action.action_type == const.CASE_ACTION_CREATE:
                    if phone_owns_case:
                        self._add_primary_case(case._id)
                        made_changes = True
                elif action.action_type == const.CASE_ACTION_UPDATE:
                    if not phone_owns_case:
                        # we must have just changed the owner_id to something we didn't own
                        # we can try pruning this case since it's no longer relevant
                        self.prune_case(case._id)
                        made_changes = True
                    else:
                        if case._id in self.dependent_case_ids_on_phone:
                            self.dependent_case_ids_on_phone.remove(case._id)
                            made_changes = True
                elif action.action_type == const.CASE_ACTION_INDEX:
                    # we should never have to do anything with case IDs here since the
                    # indexed case should already be on the phone.
                    # however, we should update our index tree accordingly
                    for index in action.indices:
                        if index.referenced_id:
                            self.index_tree.set_index(case._id, index.identifier, index.referenced_id)
                            if index.referenced_id not in self.case_ids_on_phone:
                                self.case_ids_on_phone.add(index.referenced_id)
                                self.dependent_case_ids_on_phone.add(index.referenced_id)
                        else:
                            self.index_tree.delete_index(case._id, index.identifier)
                        made_changes = True
                elif action.action_type == const.CASE_ACTION_CLOSE:
                    # this case is being closed.
                    # we can try pruning this case since it's no longer relevant
                    self.prune_case(case._id)
                    made_changes = True

        logger.debug('case ids after update: {}'.format(', '.join(self.case_ids_on_phone)))
        logger.debug('dependent case ids after update: {}'.format(', '.join(self.dependent_case_ids_on_phone)))
        # if made_changes or case_list:
        #     try:
        #         if made_changes:
        #             self.save()
        #         if case_list:
        #             self.invalidate_cached_payloads()
        #     except ResourceConflict:
        #         logging.exception('doc update conflict saving sync log {id}'.format(
        #             id=self._id,
        #         ))
        #         raise
        return made_changes
