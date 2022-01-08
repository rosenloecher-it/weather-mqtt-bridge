import unittest
from datetime import timedelta, datetime
from unittest import mock

from src.fetcher.time_series import MaxTimeSeries


class TestMaxTimeSeries(unittest.TestCase):

    @mock.patch('src.time_utils.TimeUtils.now')
    def test_standard(self, mocked_now):

        c = MaxTimeSeries("dummy", timedelta(seconds=20))

        mocked_now.return_value = datetime(2019, 1, 1, 1, 1, 0)
        s1 = None
        so = c.collect_and_deliver(s1)
        self.assertEqual(so, s1)

        mocked_now.return_value = datetime(2019, 1, 1, 1, 1, 1)
        s1 = 1
        so = c.collect_and_deliver(s1)
        self.assertEqual(so, s1)

        mocked_now.return_value = datetime(2019, 1, 1, 1, 1, 5)
        s2 = 5
        so = c.collect_and_deliver(s2)
        self.assertEqual(so, s2)

        mocked_now.return_value = datetime(2019, 1, 1, 1, 1, 30)
        s3 = 2
        so = c.collect_and_deliver(s3)
        self.assertEqual(so, s3)

        # last value None
        mocked_now.return_value = datetime(2019, 1, 1, 1, 1, 31)
        so = c.collect_and_deliver(None)
        self.assertEqual(so, s3)

        # last value None
        mocked_now.return_value = datetime(2019, 1, 1, 1, 1, 32)
        s5 = 1
        so = c.collect_and_deliver(s5)
        self.assertEqual(so, s3)
