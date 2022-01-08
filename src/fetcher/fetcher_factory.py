import copy

from src.fetcher.froggit_wh2600_job import FroggitWh2600Job
from src.fetcher.time_series_manager import TimeSeriesManager


class FetcherFactory:

    def __init__(self, fetcher_config):
        self._fetcher_config = copy.deepcopy(fetcher_config)
        self._time_series_manager = TimeSeriesManager()

    def create_fetcher_job(self):
        return FroggitWh2600Job(self._fetcher_config, self._time_series_manager)
