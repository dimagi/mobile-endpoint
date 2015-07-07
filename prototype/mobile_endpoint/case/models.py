import copy
from datetime import datetime
from functools import cmp_to_key
import re
import sys

from jsonobject.api import JsonObject
from jsonobject.exceptions import BadValueError
from jsonobject.properties import StringProperty, DateTimeProperty, DictProperty, ListProperty, BooleanProperty

from mobile_endpoint.case import const
from mobile_endpoint.exceptions import ReconciliationError, MissingServerDate
from mobile_endpoint.form.form_processing import is_override, is_deprecation


class CommCareCaseIndex(JsonObject):
    """
    In CaseXML v2 we support indices, which link a case to other cases.
    """
    identifier = StringProperty()
    referenced_type = StringProperty()
    referenced_id = StringProperty()

    @classmethod
    def from_case_index_update(cls, index):
        return cls(identifier=index.identifier,
                   referenced_type=index.referenced_type,
                   referenced_id=index.referenced_id)

    def __unicode__(self):
        return "%(identifier)s ref: (type: %(ref_type)s, id: %(ref_id)s)" % \
                {"identifier": self.identifier,
                 "ref_type": self.referenced_type,
                 "ref_id": self.referenced_id}

    def __cmp__(self, other):
        return cmp(unicode(self), unicode(other))

    def __repr__(self):
        return str(self)


class CommCareCaseAction(JsonObject):
    """
    An atomic action on a case. Either a create, update, or close block in
    the xml.
    """
    action_type = StringProperty(choices=list(const.CASE_ACTIONS))
    user_id = StringProperty()
    date = DateTimeProperty()
    server_date = DateTimeProperty()
    xform_id = StringProperty()
    xform_xmlns = StringProperty()
    xform_name = StringProperty()
    sync_log_id = StringProperty()

    updated_known_properties = DictProperty()
    updated_unknown_properties = DictProperty()
    indices = ListProperty(CommCareCaseIndex)
    # attachments = DictProperty(CommCareCaseAttachment)

    deprecated = False

    @classmethod
    def from_parsed_action(cls, date, user_id, xformdoc, action):
        if not action.action_type_slug in const.CASE_ACTIONS:
            raise ValueError("%s not a valid case action!" % action.action_type_slug)

        ret = CommCareCaseAction(action_type=action.action_type_slug, date=date, user_id=user_id)

        ret.server_date = xformdoc.received_on
        ret.xform_id = xformdoc.id
        ret.xform_xmlns = xformdoc.xmlns
        ret.xform_name = xformdoc.name
        ret.updated_known_properties = action.get_known_properties()

        ret.updated_unknown_properties = action.dynamic_properties
        ret.indices = [CommCareCaseIndex.from_case_index_update(i) for i in action.indices]
        # ret.attachments = dict((attach_id, CommCareCaseAttachment.from_case_index_update(attach))
        #                        for attach_id, attach in action.attachments.items())
        if hasattr(xformdoc, "last_sync_token"):
            ret.sync_log_id = xformdoc.last_sync_token
        return ret

    def __repr__(self):
        return "{xform}: {type} - {date} ({server_date})".format(
            xform=self.xform_id, type=self.action_type,
            date=self.date, server_date=self.server_date
        )


class IndexHoldingMixIn(object):
    """
    Since multiple objects need this functionality, implement it as a mixin
    """

    def has_index(self, id):
        return id in (i.identifier for i in self.indices)

    def get_index(self, id):
        found = filter(lambda i: i.identifier == id, self.indices)
        if found:
            assert(len(found) == 1)
            return found[0]
        return None

    def get_index_by_ref_id(self, doc_id):
        found = filter(lambda i: i.referenced_id == doc_id, self.indices)
        if found:
            assert(len(found) == 1)
            return found[0]
        return None

    def update_indices(self, index_update_list):
        for index_update in index_update_list:
            if index_update.referenced_id:
                # NOTE: used to check the existence of the referenced
                # case here but is moved into the pre save processing
                pass
            if self.has_index(index_update.identifier):
                if not index_update.referenced_id:
                    # empty ID = delete
                    self.indices.remove(self.get_index(index_update.identifier))
                else:
                    # update
                    index = self.get_index(index_update.identifier)
                    index.referenced_type = index_update.referenced_type
                    index.referenced_id = index_update.referenced_id
            else:
                # no id, no index
                if index_update.referenced_id:
                    self.indices.append(CommCareCaseIndex(identifier=index_update.identifier,
                                                          referenced_type=index_update.referenced_type,
                                                          referenced_id=index_update.referenced_id))

    def remove_index_by_ref_id(self, doc_id):
        index = self.get_index_by_ref_id(doc_id)
        if not index:
            raise ValueError('index with id %s not found in doc %s' % (id, self._id))
        self.indices.remove(index)


class CommCareCase(JsonObject, IndexHoldingMixIn):
    """
    A case, taken from casexml.  This represents the latest
    representation of the case - the result of playing all
    the actions in sequence.
    """
    doc_type = 'CommCareCase'
    domain = StringProperty()
    export_tag = ListProperty(unicode)
    xform_ids = ListProperty(unicode)

    external_id = StringProperty()
    opened_on = DateTimeProperty()
    modified_on = DateTimeProperty()
    type = StringProperty()
    closed = BooleanProperty(default=False)
    closed_on = DateTimeProperty()
    user_id = StringProperty()
    owner_id = StringProperty()
    opened_by = StringProperty()
    closed_by = StringProperty()

    actions = ListProperty(CommCareCaseAction)
    name = StringProperty()
    version = StringProperty()
    indices = ListProperty(CommCareCaseIndex)
    # case_attachments = DictProperty(CommCareCaseAttachment)

    server_modified_on = DateTimeProperty()

    def __unicode__(self):
        return "CommCareCase: %s (%s)" % (self.case_id, self.get_id)

    def __setattr__(self, key, value):
        # todo: figure out whether we can get rid of this.
        # couchdbkit's auto-type detection gets us into problems for various
        # workflows here, so just force known string properties to strings
        # before setting them. this would just end up failing hard later if
        # it wasn't a string
        _STRING_ATTRS = ('external_id', 'user_id', 'owner_id', 'opened_by',
                         'closed_by', 'type', 'name')
        if key in _STRING_ATTRS:
            value = unicode(value or '')
        super(CommCareCase, self).__setattr__(key, value)

    def __get_case_id(self):
        return self.id

    def __set_case_id(self, id):
        self.id = id

    case_id = property(__get_case_id, __set_case_id)

    def __repr__(self):
        return "%s(name=%r, type=%r, id=%r)" % (
                self.__class__.__name__, self.name, self.type, self.id)

    @property
    def server_opened_on(self):
        try:
            open_action = self.actions[0]
            return open_action.server_date
        except Exception:
            pass

    @property
    def has_indices(self):
        return self.indices or self.reverse_indices

    def get_json(self, lite=False):
        ret = {
            # actions excluded here
            "domain": self.domain,
            "case_id": self.case_id,
            "user_id": self.user_id,
            "closed": self.closed,
            "date_closed": self.closed_on,
            "xform_ids": self.xform_ids,
            # renamed
            "date_modified": self.modified_on,
            "version": self.version,
            # renamed
            "server_date_modified": self.server_modified_on,
            # renamed
            "server_date_opened": self.server_opened_on,
            "properties": dict(self.dynamic_case_properties() + {
                "external_id": self.external_id,
                "owner_id": self.owner_id,
                # renamed
                "case_name": self.name,
                # renamed
                "case_type": self.type,
                # renamed
                "date_opened": self.opened_on,
                # all custom properties go here
            }.items()),
            #reorganized
            "indices": self.get_index_map(),
            # "attachments": self.get_attachment_map(),
        }
        if not lite:
            ret.update({
                "reverse_indices": self.get_index_map(True),
            })
        return ret

    # def get_attachment_map(self):
    #     return dict([
    #         (name, {
    #             'url': self.get_attachment_server_url(att.attachment_key),
    #             'mime': att.attachment_from
    #         }) for name, att in self.case_attachments.items()
    #     ])

    def get_index_map(self):  #, reversed=False):
        return dict([
            (index.identifier, {
                "case_type": index.referenced_type,
                "case_id": index.referenced_id
            }) for index in self.indices  # if not reversed else self.reverse_indices)
        ])

    def get_case_property(self, property):
        try:
            return getattr(self, property)
        except Exception:
            return None

    def set_case_property(self, property, value):
        setattr(self, property, value)

    def case_properties(self):
        return self.to_json()

    def get_actions_for_form(self, form_id):
        return [a for a in self.actions if a.xform_id == form_id]

    def get_version_token(self):
        """
        A unique token for this version.
        """
        # in theory since case ids are unique and modification dates get updated
        # upon any change, this is all we need
        return "%s::%s" % (self.case_id, self.modified_on)


    @classmethod
    def from_case_update(cls, case_update, xformdoc):
        """
        Create a case object from a case update object.
        """
        assert not is_deprecation(xformdoc)  # you should never be able to create a case from a deleted update
        case = cls()
        case.id = case_update.id
        case.modified_on = datetime.utcnow() # parsing.string_to_utc_datetime(case_update.modified_on_str) \
                            #if case_update.modified_on_str else

        # apply initial updates, if present
        case.update_from_case_update(case_update, xformdoc)
        return case

    def update_from_case_update(self, case_update, xformdoc, other_forms=None):
        # if case_update.has_referrals():
        #     logging.error('Form {} touching case {} in domain {} is still using referrals'.format(
        #         xformdoc.id, case_update.id, getattr(xformdoc, 'domain', None))
        #     )
        #     raise UsesReferrals(_('Sorry, referrals are no longer supported!'))

        if is_deprecation(xformdoc):
            # Mark all of the form actions as deprecated. These will get removed on rebuild.
            # This assumes that there is a second update coming that will actually
            # reapply the equivalent actions from the form that caused the current
            # one to be deprecated (which is what happens in form processing).
            for a in self.actions:
                if a.xform_id == xformdoc.orig_id:
                    a.deprecated = True

            # short circuit the rest of this since we don't actually want to
            # do any case processing
            return
        elif is_override(xformdoc):
            # This form is overriding a deprecated form.
            # Apply the actions just after the last action with this form type.
            # This puts the overriding actions in the right order relative to the others.
            prior_actions = [a for a in self.actions if a.xform_id == xformdoc.id]
            if prior_actions:
                action_insert_pos = self.actions.index(prior_actions[-1]) + 1
                # slice insertion
                # http://stackoverflow.com/questions/7376019/python-list-extend-to-index/7376026#7376026
                self.actions[action_insert_pos:action_insert_pos] = case_update.get_case_actions(xformdoc)
            else:
                self.actions.extend(case_update.get_case_actions(xformdoc))
        else:
            # normal form - just get actions and apply them on the end
            self.actions.extend(case_update.get_case_actions(xformdoc))

        # rebuild the case
        local_forms = {xformdoc.id: xformdoc}
        local_forms.update(other_forms or {})
        self.rebuild(strict=False, xforms=local_forms)

        if case_update.version:
            self.version = case_update.version

    def _apply_action(self, action, xform):
        if action.action_type == const.CASE_ACTION_CREATE:
            self.apply_create(action)
        elif action.action_type == const.CASE_ACTION_UPDATE:
            self.apply_updates(action)
        elif action.action_type == const.CASE_ACTION_INDEX:
            self.update_indices(action.indices)
        elif action.action_type == const.CASE_ACTION_CLOSE:
            self.apply_close(action)
        elif action.action_type == const.CASE_ACTION_ATTACHMENT:
            self.apply_attachments(action, xform)
        elif action.action_type in (const.CASE_ACTION_COMMTRACK, const.CASE_ACTION_REBUILD):
            return  # no action needed here, it's just a placeholder stub
        else:
            raise ValueError("Can't apply action of type %s: %s" % (
                action.action_type,
                self.get_id,
            ))

        # override any explicit properties from the update
        if action.user_id:
            self.user_id = action.user_id
        if self.modified_on is None or action.date > self.modified_on:
            self.modified_on = action.date

    def apply_create(self, create_action):
        """
        Applies a create block to a case.

        Note that all unexpected attributes are ignored (thrown away)
        """
        for k, v in create_action.updated_known_properties.items():
            setattr(self, k, v)

        if not self.opened_on:
            self.opened_on = create_action.date
        if not self.opened_by:
            self.opened_by = create_action.user_id

    def apply_updates(self, update_action):
        """
        Applies updates to a case
        """
        for k, v in update_action.updated_known_properties.items():
            setattr(self, k, v)

        properties = self.properties()
        for item in update_action.updated_unknown_properties:
            if item not in const.CASE_TAGS:
                value = update_action.updated_unknown_properties[item]
                if isinstance(properties.get(item), StringProperty):
                    value = unicode(value)
                try:
                    self[item] = value
                except BadValueError:
                    # notify_exception(None, "Can't set property {} on case {} from form {}".format(
                    #     item, self.id, update_action.xform_id
                    # ))
                    raise

    def apply_close(self, close_action):
        self.closed = True
        self.closed_on = close_action.date
        self.closed_by = close_action.user_id

    def check_action_order(self):
        action_dates = [a.server_date for a in self.actions if a.server_date]
        return action_dates == sorted(action_dates)

    def reconcile_actions(self, rebuild=False, xforms=None):
        """
        Runs through the action list and tries to reconcile things that seem
        off (for example, out-of-order submissions, duplicate actions, etc.).

        This method raises a ReconciliationError if anything goes wrong.
        """
        def _check_preconditions():
            error = None
            for a in self.actions:
                if a.server_date is None:
                    error = u"Case {0} action server_date is None: {1}"
                elif a.xform_id is None:
                    error = u"Case {0} action xform_id is None: {1}"
                if error:
                    raise ReconciliationError(error.format(self.get_id, a))

        _check_preconditions()

        # this would normally work except we only recently started using the
        # form timestamp as the modification date so we have to do something
        # fancier to deal with old data
        deduplicated_actions = list(set(self.actions))

        def _further_deduplicate(action_list):
            def actions_match(a1, a2):
                # if everything but the server_date match, the actions match.
                # this will allow for multiple case blocks to be submitted
                # against the same case in the same form so long as they
                # are different
                a1doc = copy.copy(a1._doc)
                a2doc = copy.copy(a2._doc)
                a2doc['server_date'] = a1doc['server_date']
                a2doc['date'] = a1doc['date']
                return a1doc == a2doc

            ret = []
            for a in action_list:
                found_actions = [other for other in ret if actions_match(a, other)]
                if found_actions:
                    if len(found_actions) != 1:
                        error = (u"Case {0} action conflicts "
                                 u"with multiple other actions: {1}")
                        raise ReconciliationError(error.format(self.get_id, a))
                    match = found_actions[0]
                    # when they disagree, choose the _earlier_ one as this is
                    # the one that is likely timestamped with the form's date
                    # (and therefore being processed later in absolute time)
                    ret[ret.index(match)] = a if a.server_date < match.server_date else match
                else:
                    ret.append(a)
            return ret

        deduplicated_actions = _further_deduplicate(deduplicated_actions)
        sorted_actions = sorted(
            deduplicated_actions,
            key=_action_sort_key_function(self)
        )
        if sorted_actions:
            if sorted_actions[0].action_type != const.CASE_ACTION_CREATE:
                error = u"Case {0} first action not create action: {1}"
                raise ReconciliationError(
                    error.format(self.get_id, sorted_actions[0])
                )
        self.actions = sorted_actions
        if rebuild:
            # it's pretty important not to block new case changes
            # just because previous case changes have been bad
            self.rebuild(strict=False, xforms=xforms)

    def rebuild(self, strict=True, xforms=None):
        """
        Rebuilds the case state in place from its actions.

        If strict is True, this will enforce that the first action must be a create.
        """
        from mobile_endpoint.case.cleanup import reset_state

        xforms = xforms or {}
        reset_state(self)
        # try to re-sort actions if necessary
        try:
            self.actions = sorted(self.actions, key=_action_sort_key_function(self))
        except MissingServerDate:
            # only worry date reconciliation if in strict mode
            if strict:
                raise

        # remove all deprecated actions during rebuild.
        self.actions = [a for a in self.actions if not a.deprecated]
        actions = copy.deepcopy(list(self.actions))

        if strict:
            if actions[0].action_type != const.CASE_ACTION_CREATE:
                error = u"Case {0} first action not create action: {1}"
                raise ReconciliationError(
                    error.format(self.get_id, self.actions[0])
                )

        for a in actions:
            self._apply_action(a, xforms.get(a.xform_id))

        self.xform_ids = []
        for a in self.actions:
            if a.xform_id and a.xform_id not in self.xform_ids:
                self.xform_ids.append(a.xform_id)

    def dynamic_case_properties(self):
        """(key, value) tuples sorted by key"""
        json = self.to_json()
        wrapped_case = self
        if type(self) != CommCareCase:
            wrapped_case = CommCareCase.wrap(self._doc)

        return sorted([(key, json[key]) for key in wrapped_case.dynamic_properties()
                       if re.search(r'^[a-zA-Z]', key)])


def _action_sort_key_function(case):
    def _action_cmp(first_action, second_action):
        # if the forms aren't submitted by the same user, just default to server dates
        if first_action.user_id != second_action.user_id:
            return cmp(first_action.server_date, second_action.server_date)
        else:
            form_ids = list(case.xform_ids)

            def _sortkey(action):
                if not action.server_date or not action.date:
                    raise MissingServerDate()

                form_cmp = lambda form_id: (form_ids.index(form_id)
                                            if form_id in form_ids else sys.maxint, form_id)
                # if the user is the same you should compare with the special logic below
                # if the user is not the same you should compare just using received_on
                return (
                    # this is sneaky - it's designed to use just the date for the
                    # server time in case the phone submits two forms quickly out of order
                    action.server_date.date(),
                    action.date,
                    form_cmp(action.xform_id),
                    _type_sort(action.action_type),
                )

            return cmp(_sortkey(first_action), _sortkey(second_action))

    return cmp_to_key(_action_cmp)


def _type_sort(action_type):
    """
    Consistent ordering for action types
    """
    return const.CASE_ACTIONS.index(action_type)
