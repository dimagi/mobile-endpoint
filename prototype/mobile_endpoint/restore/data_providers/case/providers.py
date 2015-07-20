from mobile_endpoint.restore.data_providers.case.clean_owners import get_case_payload
from mobile_endpoint.restore.data_providers.standard import LongRunningRestoreDataProvider


class CasePayloadProvider(LongRunningRestoreDataProvider):
    """
    Long running restore provider responsible for generating the case and stock payloads.
    """
    def get_response(self, restore_state):
        # if restore_state.use_clean_restore:
        return get_case_payload(restore_state)
        # else:
        #     return _batched_response(restore_state)

