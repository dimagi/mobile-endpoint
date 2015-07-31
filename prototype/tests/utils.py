from datetime import datetime
from uuid import uuid4
from lxml import etree
from mobile_endpoint.backends.manager import get_dao
from mobile_endpoint.models import Synclog, db
from mobile_endpoint.synclog.checksum import Checksum
from mobile_endpoint.synclog.models import SimplifiedSyncLog, IndexTree


def check_xml_line_by_line(expected, actual):
    """Does what it's called, hopefully parameters are self-explanatory"""
    # this is totally wacky, but elementtree strips needless
    # whitespace that mindom will preserve in the original string
    parser = etree.XMLParser(remove_blank_text=True)
    parsed_expected = etree.tostring(etree.XML(expected, parser), pretty_print=True)
    parsed_actual = etree.tostring(etree.XML(actual, parser), pretty_print=True)
    
    if parsed_expected == parsed_actual:
        return

    try:
        expected_lines = parsed_expected.split("\n")
        actual_lines = parsed_actual.split("\n")
        assert len(expected_lines) == len(actual_lines), ("Parsed xml files are different lengths\n" +
            "Expected: \n%s\nActual:\n%s" % (parsed_expected, parsed_actual))

        for i in range(len(expected_lines)):
            assert expected_lines[i] == actual_lines[i]

    except AssertionError:
        import logging
        logging.error("Failure in xml comparison\nExpected:\n%s\nActual:\n%s" % (parsed_expected, parsed_actual))
        raise


def create_synclog(backend, domain, user_id, owner_ids=None, case_ids=None, dependent_case_ids=None, index_tree=None):
    dao = get_dao(backend)
    synclog_id = str(uuid4())
    generic = SimplifiedSyncLog(
        id=synclog_id,
        date=datetime.utcnow(),
        domain=domain,
        user_id=user_id,
        owner_ids_on_phone=set(owner_ids or [user_id]),
        case_ids_on_phone=set(case_ids or []),
        dependent_case_ids_on_phone=set(dependent_case_ids or []),
        index_tree=IndexTree(indices=index_tree or {})
    )
    dao.save_synclog(generic)
    return synclog_id
