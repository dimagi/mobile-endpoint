from datetime import date
from flask import request
from mobile_endpoint.dao import SQLDao

from mobile_endpoint.extensions import requires_auth
from mobile_endpoint.views import ota_mod
from mobile_endpoint.restore.restore import User as CaseXMLUser, RestoreConfig, RestoreParams, RestoreCacheSettings
from tests.dummy import dummy_user


@ota_mod.route('/restore/<domain>', methods=['GET'])
@requires_auth
def ota_restore(domain):
    user_id = request.args.get('user_id')
    restore_params = get_restore_params(request)

    dao = SQLDao()
    restore_config = RestoreConfig(
        dao=dao,
        project=Domain(domain),
        user=get_user(user_id),
        params=RestoreParams(**restore_params),
        cache_settings=RestoreCacheSettings(),
    )
    response = restore_config.get_response()
    dao.commit_restore(restore_config.restore_state)
    return response

def get_restore_params(request):
    """
    Given a request, get the relevant restore parameters out with sensible defaults
    """
    # not a view just a view util
    return {
        'sync_log_id': request.args.get('since'),
        'version': request.args.get('version', "1.0"),
        'state_hash': request.args.get('state'),
        'include_item_count': request.args.get('items') == 'true',
        'force_restore_mode': request.args.get('mode', None)
    }


def get_user(user_id):
    return dummy_user(user_id)


class Domain(object):
    def __init__(self, name):
        self.name = name