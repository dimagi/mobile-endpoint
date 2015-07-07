import logging
from mobile_endpoint.case import const
from mobile_endpoint.case.xml.parser import KNOWN_PROPERTIES

logger = logging.getLogger(__name__)


def primary_actions(case):
    return filter(lambda a: a.action_type != const.CASE_ACTION_REBUILD,
                  case.actions)


def reset_state(case):
    """
    Clear known case properties, and all dynamic properties
    """
    dynamic_properties = set([k for action in case.actions for k in action.updated_unknown_properties.keys()])
    for k in dynamic_properties:
        try:
            delattr(case, k)
        except KeyError:
            pass
        except AttributeError:
            # 'case_id' is not a valid property so don't worry about spamming
            # this error.
            if k != 'case_id':
                logger.error(
                    "Cannot delete attribute '%(attribute)s' from case '%(case_id)s'" % {
                        'case_id': case.id,
                        'attribute': k,
                    }
                )

    # already deleted means it was explicitly set to "deleted",
    # as opposed to getting set to that because it has no actions
    already_deleted = case.doc_type == 'CommCareCase-Deleted' and primary_actions(case)
    if not already_deleted:
        case.doc_type = 'CommCareCase'

    # hard-coded normal properties (from a create block)
    for prop, default_value in KNOWN_PROPERTIES.items():
        setattr(case, prop, default_value)

    case.closed = False
    case.modified_on = None
    case.closed_on = None
    case.closed_by = ''
    return case
