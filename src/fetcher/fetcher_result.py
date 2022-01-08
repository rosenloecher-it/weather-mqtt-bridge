from collections import namedtuple


class FetcherStatus:
    SUCCESS = "success"
    TIMEOUT = "timeout"
    ERROR = "error"


FetcherResult = namedtuple('FetcherResult', ['status', 'values'])  # status: FetcherStatus, values: Dict[str, any]
