from collections import namedtuple
import copy
from datetime import datetime
import logging

from mobile_endpoint.case import const
from mobile_endpoint.case.models import CommCareCase
from mobile_endpoint.case.xml.parser import case_update_from_block
from mobile_endpoint.dao import CaseDbCache
from mobile_endpoint.exceptions import ReconciliationError
from mobile_endpoint.form.form_processing import is_deprecation
from mobile_endpoint.form.models import XFormInstance


logger = logging.getLogger(__name__)


def process_cases_in_form(xform, dao):
    with CaseDbCache(dao, domain=xform['domain'],
                     lock=True, deleted_ok=True, xforms=[xform]) as case_db:
        case_result = _get_or_update_cases([xform], case_db)
        cases = case_result.cases

        for case in cases:
            case['server_modified_on'] = datetime.utcnow()
            case_db.mark_changed(case)
            if not case.check_action_order():
                try:
                    case.reconcile_actions(rebuild=True, xforms={xform.id: xform})
                except ReconciliationError:
                    pass

        # todo: check that cases haven't been modified since we loaded them (why not use locking?)

        if xform.last_sync_token:
            relevant_log = case_db.dao.get_synclog(xform.last_sync_token)
            if relevant_log:
                if relevant_log.update_phone_lists(xform, cases):
                    case_result.set_synclog(relevant_log)

        case_result.set_cases(case_db.get_changed())
        return case_result


def _get_or_update_cases(xforms, case_db):
    """
    Given an xform document, update any case blocks found within it,
    returning a dictionary mapping the case ids affected to the
    couch case document objects
    """
    # have to apply the deprecations before the updates
    sorted_forms = sorted(xforms, key=lambda f: 0 if is_deprecation(f) else 1)
    for xform in sorted_forms:
        for case_update in get_case_updates(xform):
            case_doc = _get_or_update_model(case_update, xform, case_db)
            if case_doc:
                case_db.set(case_doc['id'], case_doc)

    # at this point we know which cases we want to update so copy this away
    # this prevents indices that end up in the cache from being added to the return value
    touched_cases = copy.copy(case_db.cache)

    # once we've gotten through everything, validate all indices
    # and check for new dirtiness flags
    def _validate_indices(case):
        dirtiness_flags = []
        is_dirty = False
        if case['indices']:
            for index in case['indices']:
                # call get and not doc_exists to force domain checking
                # see CaseDbCache.validate_doc
                referenced_case = case_db.get(index['referenced_id'])
                if not referenced_case:
                    # just log, don't raise an error or modify the index
                    logger.error(
                        "Case '%s' references non-existent case '%s'",
                        case.id,
                        index.referenced_id,
                    )
                else:
                    if referenced_case['owner_id'] != case['owner_id']:
                        is_dirty = True
        if is_dirty:
            dirtiness_flags.append(DirtinessFlag(case.id, case.owner_id))
        return dirtiness_flags

    def _get_dirtiness_flags_for_child_cases(domain, cases):
        child_cases = case_db.dao.get_reverse_indexed_cases(domain, [c['id'] for c in cases])
        case_owner_map = dict((case.id, case.owner_id) for case in cases)
        for child_case in child_cases:
            for index in child_case.indices:
                if (index.referenced_id in case_owner_map
                        and child_case.owner_id != case_owner_map[index.referenced_id]):
                    yield DirtinessFlag(child_case.id, child_case.owner_id)

    dirtiness_flags = [flag for case in case_db.cache.values() for flag in _validate_indices(case)]
    domain = getattr(case_db, 'domain', None)
    track_cleanliness = True #should_track_cleanliness(domain)
    if track_cleanliness and touched_cases:
        # only do this extra step if the toggle is enabled since we know we aren't going to
        # care about the dirtiness flags otherwise.
        dirtiness_flags += list(_get_dirtiness_flags_for_child_cases(domain, touched_cases.values()))
    return CaseProcessingResult(domain, touched_cases.values(), dirtiness_flags, track_cleanliness)


# Lightweight class used to store the dirtyness of a case/owner pair.
DirtinessFlag = namedtuple('DirtinessFlag', ['case_id', 'owner_id'])


class CaseProcessingResult(object):
    """
    Lightweight class used to collect results of case processing
    """
    def __init__(self, domain, cases, dirtiness_flags, track_cleanliness):
        self.domain = domain
        self.cases = cases
        self.dirtiness_flags = dirtiness_flags
        self.track_cleanliness = track_cleanliness
        self.synclog = None

    def get_clean_owner_ids(self):
        dirty_flags = self.get_flags_to_save()
        return {c.owner_id for c in self.cases if c.owner_id and c.owner_id not in dirty_flags}

    def set_cases(self, cases):
        self.cases = cases

    def set_synclog(self, synclog):
        self.synclog = synclog

    def get_flags_to_save(self):
        return {f.owner_id: f.case_id for f in self.dirtiness_flags}

    # def commit_dirtiness_flags(self):
    #     """
    #     Updates any dirtiness flags in the database.
    #     """
    #     if self.track_cleanliness and self.domain:
    #         flags_to_save = self.get_flags_to_save()
    #         if should_create_flags_on_submission(self.domain):
    #             assert settings.UNIT_TESTING  # this is currently only true when unit testing
    #             all_touched_ids = set(flags_to_save.keys()) | self.get_clean_owner_ids()
    #             to_update = {f.owner_id: f for f in OwnershipCleanlinessFlag.objects.filter(
    #                 domain=self.domain,
    #                 owner_id__in=list(all_touched_ids),
    #             )}
    #             for owner_id in all_touched_ids:
    #                 if owner_id not in to_update:
    #                     # making from scratch - default to clean, but set to dirty if needed
    #                     flag = OwnershipCleanlinessFlag(domain=self.domain, owner_id=owner_id, is_clean=True)
    #                     if owner_id in flags_to_save:
    #                         flag.is_clean = False
    #                         flag.hint = flags_to_save[owner_id]
    #                     flag.save()
    #                 else:
    #                     # updating - only save if we are marking dirty or setting a hint
    #                     flag = to_update[owner_id]
    #                     if owner_id in flags_to_save and (flag.is_clean or not flag.hint):
    #                         flag.is_clean = False
    #                         flag.hint = flags_to_save[owner_id]
    #                         flag.save()
    #         else:
    #             # only update the flags that are already in the database
    #             flags_to_update = OwnershipCleanlinessFlag.objects.filter(
    #                 Q(domain=self.domain),
    #                 Q(owner_id__in=flags_to_save.keys()),
    #                 Q(is_clean=True) | Q(hint__isnull=True)
    #             )
    #             for flag in flags_to_update:
    #                 flag.is_clean = False
    #                 flag.hint = flags_to_save[flag.owner_id]
    #                 flag.save()


def get_case_updates(xform):
    return [case_update_from_block(cb) for cb in extract_case_blocks(xform)]


def _get_or_update_model(case_update, xform, case_db):
    """
    Gets or updates an existing case, based on a block of data in a
    submitted form.  Doesn't save anything.
    """
    case = case_db.get(case_update.id)
    if case is None:
        case = CommCareCase.from_case_update(case_update, xform)
        case.domain = xform.domain
        return case
    else:
        case.update_from_case_update(case_update, xform, case_db.get_cached_forms())
        return case


def extract_case_blocks(doc):
    """
    Extract all case blocks from a document, returning an array of dictionaries
    with the data in each case.

    The json returned is not normalized for casexml version;
    for that get_case_updates is better.

    """

    if isinstance(doc, XFormInstance):
        doc = doc.form
    return list(_extract_case_blocks(doc))


def _extract_case_blocks(data):
    """
    helper for extract_case_blocks

    data must be json representing a node in an xform submission

    """
    if isinstance(data, list):
        for item in data:
            for case_block in _extract_case_blocks(item):
                yield case_block
    elif isinstance(data, dict) and not is_device_report(data):
        for key, value in data.items():
            if const.CASE_TAG == key:
                # it's a case block! Stop recursion and add to this value
                if isinstance(value, list):
                    case_blocks = value
                else:
                    case_blocks = [value]

                for case_block in case_blocks:
                    if has_case_id(case_block):
                        yield case_block
            else:
                for case_block in _extract_case_blocks(value):
                    yield case_block
    else:
        return


def has_case_id(case_block):
    return const.CASE_TAG_ID in case_block or const.CASE_ATTR_ID in case_block


def is_device_report(doc):
    """exclude device reports"""
    device_report_xmlns = "http://code.javarosa.org/devicereport"
    def _from_form_dict(doc):
        return "@xmlns" in doc and doc["@xmlns"] == device_report_xmlns
    def _from_xform_instance(doc):
        return "xmlns" in doc and doc["xmlns"] == device_report_xmlns

    return _from_form_dict(doc) or _from_xform_instance(doc)
