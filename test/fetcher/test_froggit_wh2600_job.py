import datetime
import unittest
from unittest import mock

from src.fetcher.fetcher_key import FetcherKey
from src.fetcher.froggit_wh2600_job import FroggitWh2600Job
from src.fetcher.time_series_manager import TimeSeriesManager
from test.setup_test import SetupTest


class _MockedFetcherJob(FroggitWh2600Job):

    mock_time = None

    def __init__(self, config, time_series_manager: TimeSeriesManager, file_name):
        super().__init__(config, time_series_manager)

        self._file_name = file_name

    def _load_page(self) -> str:
        return SetupTest.load_froggit_mocked_html(self._file_name)


class TestFroggitWh2600Job(unittest.TestCase):

    EXPECTED_VALUES = {
        FetcherKey.BATTERY_INSIDE: 'Normal',
        FetcherKey.BATTERY_OUTSIDE: 'Normal',
        FetcherKey.HUMI_INSIDE: 64.0,
        FetcherKey.HUMI_OUTSIDE: 43.0,
        FetcherKey.PRESSURE_ABS: 991.0,
        FetcherKey.PRESSURE_REL: 1019.7,
        FetcherKey.RAIN_COUNTER: 0.0,
        FetcherKey.RAIN_HOURLY: 0.0,
        FetcherKey.SOLAR_RADIATION: 637.87,
        FetcherKey.STATUS: "ok",
        FetcherKey.TEMP_INSIDE: 24.0,
        FetcherKey.TEMP_OUTSIDE: 31.3,
        FetcherKey.TIMESTAMP: "2019-08-25T14:04:00+02:00",
        FetcherKey.UVI: 4.0,
        FetcherKey.WIND_DIRECTION: 121.0,
        FetcherKey.WIND_GUST: 12.2,
        FetcherKey.WIND_SPEED: 4.0,
    }

    @mock.patch('src.utils.time_utils.TimeUtils.now')
    def test_firmware_v228(self, mocked_now):
        # def test_standard(self):
        time_series_manager = TimeSeriesManager()

        config = {
            "url": "dummy",
            "altitude": 255,
        }

        fetcher = _MockedFetcherJob(config, time_series_manager, "froggit_livedata_firmware_2.2.8.html")

        froggit_test_time = SetupTest.get_froggit_test_time()
        froggit_test_time = froggit_test_time.replace(tzinfo=datetime.timezone(datetime.timedelta(hours=2)))

        mocked_now.return_value = froggit_test_time

        fetcher_values = fetcher.fetch()
        self.assertEqual(self.EXPECTED_VALUES, fetcher_values)

    @mock.patch('src.utils.time_utils.TimeUtils.now')
    def test_firmware_v462(self, mocked_now):
        # def test_standard(self):
        time_series_manager = TimeSeriesManager()

        config = {
            "url": "dummy",
            "altitude": 255,
        }

        fetcher = _MockedFetcherJob(config, time_series_manager, "froggit_livedata_firmware_4.6.2.html")

        froggit_test_time = SetupTest.get_froggit_test_time()
        froggit_test_time = froggit_test_time.replace(tzinfo=datetime.timezone(datetime.timedelta(hours=2)))

        mocked_now.return_value = froggit_test_time

        fetcher_values = fetcher.fetch()
        self.assertEqual(self.EXPECTED_VALUES, fetcher_values)
