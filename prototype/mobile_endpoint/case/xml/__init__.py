V1 = "1.0"
V2 = "2.0"
DEFAULT_VERSION = V1

V2_NAMESPACE = "http://commcarehq.org/case/transaction/v2"

NS_VERSION_MAP = {
    V2: V2_NAMESPACE,
}

NS_REVERSE_LOOKUP_MAP = dict((v, k) for k, v in NS_VERSION_MAP.items())
