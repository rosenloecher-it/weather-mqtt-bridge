import abc
import datetime
import logging
from typing import Dict, Optional

from src.utils.time_utils import TimeUtils

_logger = logging.getLogger(__name__)


class Transformation(abc.ABC):

    @abc.abstractmethod
    def transform(self, raw_values: Dict[str, any]) -> any:
        pass

    @classmethod
    def convert2float(cls, value_in: str) -> Optional[float]:
        if not value_in or value_in.find("--") == 0:  # --.- or --
            value_out = None
        else:
            value_out = float(value_in)
        return value_out


class SingleTransformation(Transformation):  # noqa

    def __init__(self, value_key):
        self._value_key = value_key

    def __repr__(self) -> str:
        return '{}({})'.format(self.__class__.__name__, self._value_key)

    def get_key(self):
        return self._value_key


class FloatTransformation(SingleTransformation):

    def __init__(self, value_key):
        super().__init__(value_key)

    def transform(self, raw_values: Dict[str, str]) -> float:
        raw_value = raw_values.get(self._value_key)
        return self.convert2float(raw_value)


class StringTransformation(SingleTransformation):

    def __init__(self, value_key, trim=True):
        super().__init__(value_key)
        self._trim = trim

    def transform(self, raw_values: Dict[str, str]) -> str:
        raw_value = raw_values.get(self._value_key)
        value = str(raw_value)
        if self._trim:
            value = value.strip()
        return value


class TimeTransformation(SingleTransformation):  # noqa

    DEFAULT_TIME_FORMAT = '%H:%M %m/%d/%Y'  # '14:04 8/25/2019'

    def __init__(self, value_key, time_format=DEFAULT_TIME_FORMAT):
        super().__init__(value_key)
        self._time_format = time_format


# # not needed at moment
# class Time2StringTransformation(TimeTransformation):
#
#     DEFAULT_TIME_FORMAT = '%H:%M %m/%d/%Y'  # '14:04 8/25/2019'
#
#     def __init__(self, value_key, time_format=DEFAULT_TIME_FORMAT):
#         super().__init__(value_key, time_format)
#
#     def transform(self, raw_values: Dict[str, str]) -> datetime.datetime:
#         raw_value = raw_values.get(self._value_key)
#         value = datetime.datetime.strptime(raw_value, self._time_format)
#         return value.isoformat()


class TimeStringTransformationChecker(TimeTransformation):
    """
    1. Transforms a string to a datetime. ATTENTION: adds the local timezone if there is none!
    2. Checks if the delivered datetime is older than `outdate_sec`
    """

    def __init__(self, value_key, outdate_sec, time_format=TimeTransformation.DEFAULT_TIME_FORMAT):
        super().__init__(value_key, time_format)
        self._outdate_sec = outdate_sec

    def transform(self, raw_values: Dict[str, str]) -> datetime.datetime:
        raw_value = raw_values.get(self._value_key)
        value = datetime.datetime.strptime(raw_value, self._time_format)

        now = TimeUtils.now()

        if value.tzinfo is None:
            # WORKAROUND not nice, but manageable as long there is only the Froggit WH2660 weather station.
            value = value.replace(tzinfo=now.tzinfo)

        if self._outdate_sec is not None:
            self._check_delivery_time(value, now)

        return value.isoformat()

    def _check_delivery_time(self, delivery_time, now):
        title = 'delivery time check failed -'

        if not isinstance(delivery_time, datetime.datetime):
            raise ValueError('{} wrong time format ({})!'.format(title, type(delivery_time)))

        time_delta_seconds = (now - delivery_time).total_seconds()
        if time_delta_seconds > self._outdate_sec:
            raise ValueError('{0} outdated ({1:.0f}s)!'.format(title, time_delta_seconds))


class RelPressureTransformation(Transformation):
    """
    transform to relative pressure
    """

    TEMP_GRADIENT = 0.0065  # temperature gradient

    def __init__(self, abs_pres_key: str, temp_key: str, altitude: float):
        self._abs_pres_key = abs_pres_key  # relative pressure (hPa / mB)
        self._temp_key = temp_key  # temperature (°C) of weather station
        self._altitude = altitude  # altitude (meter) of weather station

    def transform(self, raw_values: Dict[str, str]) -> float:
        """
        Calculates the relative air pressure
        """
        t = raw_values.get(self._abs_pres_key)

        abs_press = self.convert2float(t)
        rel_pres = None

        if abs_press is not None:
            t = raw_values.get(self._temp_key)
            temp_station = self.convert2float(t)

            if temp_station is not None:
                temp_sea_level = 273.15 + temp_station + self.TEMP_GRADIENT * self._altitude  # temperature on sea level

                # print("t_in=%d => t0=%.1f" % (temp, tx))

                divisor = (1 - self.TEMP_GRADIENT * self._altitude / temp_sea_level)
                rel_pres = abs_press / divisor ** (0.03416 / self.TEMP_GRADIENT)
                rel_pres = round(rel_pres, 1)

        return rel_pres


class GustTransformation(Transformation):
    """
    Search max value from standard wind speed and gust speed
    """

    def __init__(self, speed_key: str, gust_key: str):
        self._speed_key = speed_key  # standard wind speed
        self._gust_key = gust_key  # gust speed

    def transform(self, raw_values: Dict[str, str]) -> float:
        t = raw_values.get(self._speed_key)
        speed1 = self.convert2float(t)

        t = raw_values.get(self._gust_key)
        speed2 = self.convert2float(t)

        speed = None
        if speed1 is None or speed2 is None:
            if speed1 is not None:
                speed = speed1
            if speed2 is not None:
                speed = speed2
        else:
            speed = max(speed1, speed2)
        return speed
