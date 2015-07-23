from mobile_endpoint.restore.xml import get_sync_element, get_registration_element


class RestoreDataProvider(object):
    """
    Base class for things that gives data directly to a restore.
    """

    def get_elements(self, restore_state):
        raise NotImplementedError('Need to implement this method')


class LongRunningRestoreDataProvider(object):
    """
    Base class for things that gives data optionally asynchronously to a restore.
    """

    def get_response(self, restore_state):
        raise NotImplementedError('Need to implement this method')


class SyncElementProvider(RestoreDataProvider):
    """
    Gets the initial sync element.
    """
    def get_elements(self, restore_state):
        yield get_sync_element(restore_state.current_sync_log.id)


class RegistrationElementProvider(RestoreDataProvider):
    """
    Gets the registration XML
    """
    def get_elements(self, restore_state):
        yield get_registration_element(restore_state.user)


class FixtureElementProvider(RestoreDataProvider):
    """
    Gets any associated fixtures.
    """
    def get_elements(self, restore_state):
        # fixture block
        # for fixture in generator.get_fixtures(
        #     restore_state.user,
        #     restore_state.version,
        #     restore_state.last_sync_log
        # ):
        #     yield fixture
        return []
