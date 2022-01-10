import datetime
import unittest
from unittest import mock

from src.fetcher.fetcher_key import FetcherKey
from src.fetcher.fetcher_result import FetcherStatus
from src.fetcher.froggit_wh2600_job import FroggitWh2600Job
from src.fetcher.time_series_manager import TimeSeriesManager
from test.setup_test import SetupTest


class _MockedFetcherJob(FroggitWh2600Job):

    mock_time = None

    def _load_page(self) -> str:
        return SetupTest.load_froggit_mocked_html()


class TestFroggitWh2600Job(unittest.TestCase):

    @mock.patch('src.time_utils.TimeUtils.now')
    def test_standard(self, mocked_now):
        # def test_standard(self):
        time_series_manager = TimeSeriesManager()

        config = {
            "url": "dummy",
            "altitude": 255,
        }

        fetcher = _MockedFetcherJob(config, time_series_manager)

        froggit_test_time = SetupTest.get_froggit_test_time()
        froggit_test_time = froggit_test_time.replace(tzinfo=datetime.timezone(datetime.timedelta(hours=2)))

        mocked_now.return_value = froggit_test_time

        test_result = fetcher.fetch()

        self.assertEqual(test_result.status, FetcherStatus.OK)

        expected_values = {
            FetcherKey.BATTERY_INSIDE: 'Normal',
            FetcherKey.BATTERY_OUSIDE: 'Normal',
            FetcherKey.HUMI_INSIDE: 64.0,
            FetcherKey.HUMI_OUTSIDE: 43.0,
            FetcherKey.PRESSURE_ABS: 991.0,
            FetcherKey.PRESSURE_REL: 1019.7,
            FetcherKey.RAIN_COUNTER: 0.0,
            FetcherKey.RAIN_HOURLY: 0.0,
            FetcherKey.SOLAR_RADIATION: 637.87,
            FetcherKey.TEMP_INSIDE: 24.0,
            FetcherKey.TEMP_OUTSIDE: 31.3,
            FetcherKey.TIMESTAMP: "2019-08-25T14:04:00+02:00",
            FetcherKey.UV: 1773.0,
            FetcherKey.UVI: 4.0,
            FetcherKey.WIND_DIRECTION: 121.0,
            FetcherKey.WIND_GUST: 12.2,
            FetcherKey.WIND_SPEED: 4.0,
        }

        self.assertEqual(test_result.values, expected_values)
