import threading

from src.fetcher.time_series import TimeSeries


class TimeSeriesManager:

    def __init__(self):
        self._lock = threading.Lock()

        self._items = {}

    @classmethod
    def get_time_series_key(cls, fetcher_key: str, value_key: str):
        return f"{fetcher_key}.{value_key}"

    def get_or_add_time_series(self, fetcher_key: str, blueprint: TimeSeries):
        if blueprint is None:
            return

        key = self.get_time_series_key(fetcher_key, blueprint.value_key)

        with self._lock:
            chosen = self._items.get(key)
            if chosen:
                if type(chosen) != type(blueprint):
                    raise RuntimeError("Wrong collector types!")
            else:
                self._items[key] = blueprint
                chosen = blueprint

            return chosen
