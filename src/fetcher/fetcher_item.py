import logging

from src.fetcher.time_series import TimeSeries
from src.fetcher.transformation import Transformation

_logger = logging.getLogger(__name__)


class FetcherItem:

    def __init__(self, result_key: str, html_key: str, transform: Transformation, time_series: TimeSeries = None):
        self.result_key = result_key
        self.html_key = html_key
        self.transform = transform
        self.time_series = time_series
        self.do_fetch = True

    def __repr__(self) -> str:
        return '{}({})'.format(self.__class__.__name__, self.result_key)

    @classmethod
    def get_html_tag_name(cls):
        return 'input'

    def get_html_attr_filter(self) -> dict:
        return {'name': self.html_key}
