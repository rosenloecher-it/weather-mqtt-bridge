import abc
import copy
import logging
import urllib
from typing import Dict, List

from bs4 import BeautifulSoup

from src.fetcher.fetcher_config import FetcherConfKey
from src.fetcher.fetcher_item import FetcherItem
from src.fetcher.fetcher_result import FetcherResult, FetcherStatus
from src.fetcher.time_series_manager import TimeSeriesManager


_logger = logging.getLogger(__name__)


class FetcherException(Exception):
    pass


class FetcherJob:

    def __init__(self, config, time_series_manager: TimeSeriesManager):
        super().__init__()

        self._config = copy.deepcopy(config)
        self._url = self._config[FetcherConfKey.URL]

        self._time_series_manager = time_series_manager

    @property
    def time_series_key(self):
        return self.__class__.__name__

    @abc.abstractmethod
    def _get_items(self) -> [FetcherItem]:
        raise NotImplementedError()

    def fetch_safe(self):
        try:
            return self.fetch()
        except Exception as ex:
            _logger.exception(ex)
            return FetcherResult(FetcherStatus.ERROR, {})

    def fetch(self):
        _logger.debug("fetching %s", self._url)

        items = self._get_items()

        html = self._load_page()
        values_raw = self._load_values(items, html)
        values_transformed = self._transform_values(items, values_raw)
        values_over_time = self._calculated_timed_values(items, values_transformed)

        result = FetcherResult(FetcherStatus.OK, values_over_time)
        return result

    def _load_page(self) -> str:
        try:
            with urllib.request.urlopen(self._url, timeout=10) as response:
                html = response.read()
                return html
        except urllib.error.URLError:
            raise FetcherException('could not open url ({})!'.format(self._url)) from None

    def _load_values(self, items: List[FetcherItem], html: str) -> Dict[str, str]:
        soup = BeautifulSoup(html, 'html.parser')
        values = {}

        for item in items:
            if not item.do_fetch:
                continue

            value = None

            try:
                elements = soup.find_all(item.get_html_tag_name(), attrs=item.get_html_attr_filter())
                count_elements = len(elements)
                if count_elements != 1:
                    _logger.error('expected one element, but got %d (%s)', count_elements, item)
                else:
                    soup_element = elements[0]
                    if soup_element is None:
                        _logger.error('item could not be found (%s)!', self)
                    else:
                        value = soup_element['value']

            except Exception as ex:
                value = None
                _logger.error('cannot load value (%s)!', item)
                _logger.exception(ex)

            values[item.result_key] = value

        return values

    @classmethod
    def _transform_values(cls, items: List[FetcherItem], values: Dict[str, str]):
        results = {}

        for item in items:
            try:
                value = item.transform.transform(values)
            except (TypeError, AttributeError):
                value = None
                _logger.error('cannot transform value (%s)!', item)

            results[item.result_key] = value

        return results

    def _calculated_timed_values(self, items: List[FetcherItem], values: Dict[str, str]):
        results = {}

        for item in items:
            value = values.get(item.result_key)

            time_series = self._time_series_manager.get_or_add_time_series(self.time_series_key, item.time_series)
            if time_series:
                value = time_series.collect_and_deliver(value)

            results[item.result_key] = value

        return results
