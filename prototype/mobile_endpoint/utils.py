from collections import namedtuple
import re
import iso8601
import pytz
import redis
from mobile_endpoint.extensions import redis_store

ISO_DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'

# this is like jsonobject.api.re_datetime,
# but without the "time" part being optional
# i.e. I just removed (...)? surrounding the second two lines
re_loose_datetime = re.compile("""
    ^
    (\d{4}) # year
    \D?
    (0[1-9]|1[0-2]) # month
    \D?
    ([12]\d|0[1-9]|3[01]) # day
    [ T]
    ([01]\d|2[0-3]) # hour
    \D?
    ([0-5]\d) # minute
    \D?
    ([0-5]\d)? # seconds
    \D?
    (\d{3,6})? # milliseconds
    ([zZ]|([\+-])([01]\d|2[0-3])\D?([0-5]\d)?)? # timezone
    $
    """
    , re.VERBOSE
)


def chunked(list_in, chunk_size):
    for i in xrange(0, len(list_in), chunk_size):
        yield list_in[i:i+chunk_size]


class LockManager(namedtuple('ObjectLockTuple', 'obj lock')):
    """
    A context manager that can also act like a simple tuple
    for dealing with an object and a lock

    The two following examples are equivalent, except that the context manager
    will release the lock even if an error is thrown in the body

    >>> # as a tuple
    >>> obj, lock = LockManager(obj, lock)
    >>> # do stuff...
    >>> if lock:
    ...     lock.release()

    >>> # as a context manager
    >>> with LockManager(obj, lock) as obj:
    ...     # do stuff...
    """
    def __enter__(self):
        return self.obj

    def __exit__(self, exc_type, exc_val, exc_tb):
        release_lock(self.lock, degrade_gracefully=True)


class ReleaseOnError(object):
    def __init__(self, lock):
        self.lock = lock

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            release_lock(self.lock, degrade_gracefully=True)


def acquire_lock(lock, degrade_gracefully=False, **kwargs):
    try:
        lock.acquire(**kwargs)
    except redis.ConnectionError:
        if degrade_gracefully:
            lock = None
        else:
            raise
    return lock


def release_lock(lock, degrade_gracefully=False):
    if lock:
        try:
            lock.release()
        except redis.ConnectionError:
            if not degrade_gracefully:
                raise


def get_with_lock(key, getter_fn, timeout_seconds=30):
    lock = redis_store.lock(key, timeout=timeout_seconds)
    lock = acquire_lock(lock, blocking=True)
    try:
        obj = getter_fn()
        if not obj:
            release_lock(lock)
            return LockManager(None, None)
    except:
        release_lock(lock)
        raise
    else:
        return LockManager(obj, lock)


def json_format_datetime(dt):
    """
    includes microseconds (always)
    >>> json_format_datetime(datetime.datetime(2015, 4, 8, 12, 0, 1))
    '2015-04-08T12:00:01.000000Z'
    """
    return dt.strftime(ISO_DATETIME_FORMAT)


def adjust_datetimes(data, parent=None, key=None):
    """
    find all datetime-like strings within data (deserialized json)
    and format them uniformly, in place.

    """
    # this strips the timezone like we've always done
    # todo: in the future this will convert to UTC
    if isinstance(data, basestring):
        if re_loose_datetime.match(data):
            parent[key] = json_format_datetime(
                iso8601.parse_date(data).astimezone(pytz.utc)
                .replace(tzinfo=None)
            )

    elif isinstance(data, dict):
        for key, value in data.items():
            adjust_datetimes(value, parent=data, key=key)
    elif isinstance(data, list):
        for i, value in enumerate(data):
            adjust_datetimes(value, parent=data, key=i)

    # return data, just for convenience in testing
    # this is the original input, modified, not a new data structure
    return data
