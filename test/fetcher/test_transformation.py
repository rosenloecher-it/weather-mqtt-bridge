import datetime
import unittest
from unittest import mock

from tzlocal import get_localzone

from src.fetcher.transformation import RelPressureTransformation, GustTransformation, TimeStringTransformationChecker


class TestRelPressureTransformation(unittest.TestCase):

    def test_std(self):
        t = RelPressureTransformation('AbsPress', 'outTemp', 255)

        raw = {'AbsPress': '991.00', 'outTemp': '31.3'}
        out = t.transform(raw)

        self.assertTrue(isinstance(out, float))
        self.assertAlmostEqual(out, 1019.7)


class TestGustTransformation(unittest.TestCase):

    def test_std(self):
        t = GustTransformation('windspeed', 'gustspeed')

        raw = {'windir': '121', 'windspeed': '4.0', 'gustspeed': '12.2'}
        out = t.transform(raw)

        self.assertTrue(abs(out - 12.2) <= 0.001)

        raw = {'windir': '121', 'windspeed': '24.1', 'gustspeed': '12.2'}
        out = t.transform(raw)
        self.assertAlmostEqual(out, 24.1)

    def test_invalid(self):
        t = GustTransformation('windspeed', 'gustspeed')

        raw = {'windir': '---', 'windspeed': '----', 'gustspeed': '----'}
        out = t.transform(raw)

        self.assertEqual(out, None)


class TestTimeStringTransformationChecker(unittest.TestCase):

    @classmethod
    def get_timezones(cls):
        utc = datetime.datetime.utcnow()
        tz1 = datetime.timezone(datetime.timedelta(hours=2))
        return [None, get_localzone(), utc.tzinfo, tz1]

    @mock.patch('src.time_utils.TimeUtils.now')
    def test_success(self, mocked_now):
        for tzinfo in self.get_timezones():
            # default time format: '14:04 8/25/2019'
            mocked_now.return_value = datetime.datetime(2019, 8, 25, 14, 5, 0, tzinfo=tzinfo)
            time_page_created = datetime.datetime(2019, 8, 25, 14, 3, 0, tzinfo=tzinfo)
            transformation = TimeStringTransformationChecker("result_key", 120)

            out = transformation.transform({"result_key": "14:03 8/25/2019"})
            self.assertEqual(out, time_page_created.isoformat())

    @mock.patch('src.time_utils.TimeUtils.now')
    def test_failure(self, mocked_now):
        for tzinfo in self.get_timezones():
            # default time format: '14:04 8/25/2019'
            mocked_now.return_value = datetime.datetime(2019, 8, 25, 14, 5, 0, tzinfo=tzinfo)
            transformation = TimeStringTransformationChecker("result_key", 120)

            with self.assertRaises(ValueError) as ex:
                transformation.transform({"result_key": "14:02 8/25/2019"})
            self.assertTrue("outdated" in str(ex.exception))
