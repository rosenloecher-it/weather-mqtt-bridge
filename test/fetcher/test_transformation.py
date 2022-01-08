import datetime
import unittest
from unittest import mock

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

    # @mock.patch.object(TimeStringTransformationChecker, "_now", MagicMock())

    @mock.patch('src.time_utils.TimeUtils.now')
    def test_success(self, mocked_now):
        # default time format: '14:04 8/25/2019'
        mocked_now.return_value = datetime.datetime(2019, 8, 25, 14, 5, 0)

        time_page_created = datetime.datetime(2019, 8, 25, 14, 3, 0)

        transformation = TimeStringTransformationChecker("result_key", 120)

        out = transformation.transform({"result_key": "14:03 8/25/2019"})

        self.assertEqual(out, time_page_created.isoformat())

    @mock.patch('src.time_utils.TimeUtils.now')
    def test_failure(self, mocked_now):
        # default time format: '14:04 8/25/2019'
        mocked_now.return_value = datetime.datetime(2019, 8, 25, 14, 5, 0)

        transformation = TimeStringTransformationChecker("result_key", 120)

        with self.assertRaises(ValueError) as ex:
            transformation.transform({"result_key": "14:02 8/25/2019"})

        self.assertTrue("outdated" in str(ex.exception))
