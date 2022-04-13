import copy
import threading
from collections import namedtuple
from datetime import timedelta
from typing import Optional

from src.utils.time_utils import TimeUtils


class TimeSeries:
    Tiva = namedtuple('Tiva', ['time_stamp', 'value'])

    def __init__(self, value_key):
        self._value_key = value_key

    @property
    def value_key(self):
        """Used for getting the right `TimeSeries` out of `TimeSeriesManager`"""
        return self._value_key

    def collect_and_deliver(self, value: any):
        return value  # dummy implementation


class MaxTimeSeries(TimeSeries):

    def __init__(self, value_key, time_delta: timedelta):
        super().__init__(value_key)

        self._lock = threading.Lock()
        self._time_delta = copy.deepcopy(time_delta)
        self._tivas = []

    def collect_and_deliver(self, value: Optional[float]):
        with self._lock:
            time_curr = TimeUtils.now()
            time_limit = time_curr - self._time_delta

            while len(self._tivas) > 0:
                tiva = self._tivas[0]
                if tiva.time_stamp < time_limit:
                    self._tivas.pop(0)
                else:
                    break

            if value is not None:
                self._tivas.append(self.Tiva(time_curr, value))

            max_value = None
            for tiva in self._tivas:
                if max_value is None or max_value < tiva.value:
                    max_value = tiva.value

            return max_value
