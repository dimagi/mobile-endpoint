from datetime import datetime
from mobile_endpoint.restore.restore import User

DUMMY_USERNAME = "admin"
DUMMY_PASSWORD = "secret"


def dummy_user(user_id):
    return User(user_id=user_id,
                username=DUMMY_USERNAME,
                password=DUMMY_PASSWORD,
                date_joined=datetime(2011, 6, 9),
                user_data={"something": "arbitrary"})


def dummy_user_xml(user):
        return """
    <Registration xmlns="http://openrosa.org/user/registration">
        <username>{u.username}</username>
        <password>{u.password}</password>
        <uuid>{u.user_id}</uuid>
        <date>2011-06-09</date>
        <user_data>
            <data key="commcare_first_name"/>
            <data key="commcare_last_name"/>
            <data key="something">arbitrary</data>
            <data key="commcare_phone_number"/>
        </user_data>
    </Registration>""".format(u=user)

DUMMY_RESTORE_XML_TEMPLATE = ("""
<OpenRosaResponse xmlns="http://openrosa.org/http/response"%(items_xml)s>
    <message nature="ota_restore_success">%(message)s</message>
    <Sync xmlns="http://commcarehq.org/sync">
        <restore_id>%(restore_id)s</restore_id>
    </Sync>
    %(user_xml)s
    %(case_xml)s
</OpenRosaResponse>
""")


def dummy_restore_xml(user, restore_id, case_xml="", items=None):
    return DUMMY_RESTORE_XML_TEMPLATE % {
        "restore_id": restore_id,
        "items_xml": '' if items is None else (' items="%s"' % items),
        "user_xml": dummy_user_xml(user),
        "case_xml": case_xml,
        "message": "Successfully restored account {}!".format(user.username)
    }
