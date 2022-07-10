from datetime import timedelta

from src.fetcher.fetcher_config import FetcherConfKey
from src.fetcher.fetcher_item import FetcherItem
from src.fetcher.fetcher_job import FetcherJob
from src.fetcher import transformation
from src.fetcher.fetcher_key import FetcherKey
from src.fetcher.time_series import MaxTimeSeries


class FroggitWh2600Job(FetcherJob):

    OUTDATED_TIME_IN_SECONDS = 90

    def _get_items(self) -> [FetcherItem]:
        return self.config_fetcher_items(self._config)

    @classmethod
    def config_fetcher_items(cls, config) -> [FetcherItem]:

        fetcher_items = []

        def add_standard(html_key, key, transform_class):
            key = str(key)
            fetcher_items.append(FetcherItem(key, html_key, transform_class(key)))

        # Receiver Time: "14:04 8/25/2019"
        result_key = FetcherKey.TIMESTAMP
        item = FetcherItem(
            result_key,
            "CurrTime",
            transformation.TimeStringTransformationChecker(result_key, cls.OUTDATED_TIME_IN_SECONDS)
        )
        fetcher_items.append(item)

        add_standard("outBattSta1", FetcherKey.BATTERY_OUTSIDE, transformation.StringTransformation)  # Outdoor Sensor ID and Battery
        add_standard("inBattSta", FetcherKey.BATTERY_INSIDE, transformation.StringTransformation)  # Indoor Sensor ID and Battery

        add_standard("inTemp", FetcherKey.TEMP_INSIDE, transformation.FloatTransformation)  # Indoor Temperature
        add_standard("inHumi", FetcherKey.HUMI_INSIDE, transformation.FloatTransformation)  # Indoor Humidity

        add_standard("AbsPress", FetcherKey.PRESSURE_ABS, transformation.FloatTransformation)  # Absolute Pressure

        add_standard("outTemp", FetcherKey.TEMP_OUTSIDE, transformation.FloatTransformation)  # Outdoor Temperature
        add_standard("outHumi", FetcherKey.HUMI_OUTSIDE, transformation.FloatTransformation)  # Outdoor Humidity

        add_standard("windir", FetcherKey.WIND_DIRECTION, transformation.FloatTransformation)  # Wind Direction
        # Wind Speed
        # Firmware 2.2.8
        add_standard("windspeed", FetcherKey.WIND_SPEED, transformation.FloatTransformation)
        # Firmware 4.6.2 - overwrite possible former value
        add_standard("avgwind", FetcherKey.WIND_SPEED, transformation.FloatTransformation)

        add_standard("solarrad", FetcherKey.SOLAR_RADIATION, transformation.FloatTransformation)  # Solar Radiation
        add_standard("uvi", FetcherKey.UVI, transformation.FloatTransformation)  # UVI

        add_standard("rainofhourly", FetcherKey.RAIN_HOURLY, transformation.FloatTransformation)  # Hourly Rain Rate
        add_standard("rainofyearly", FetcherKey.RAIN_COUNTER, transformation.FloatTransformation)  # Yearly Rain

        # Wind Gust
        result_key = FetcherKey.WIND_GUST
        item = FetcherItem(
            result_key,
            "gustspeed",
            transformation.GustTransformation(FetcherKey.WIND_SPEED, result_key),
            time_series=MaxTimeSeries(result_key, timedelta(minutes=15))
        )
        fetcher_items.append(item)

        # Relative Pressure "RelPress" is wrong => own calculation absolute pressure with temp + altitude
        altitude = config.get(FetcherConfKey.ALTITUDE)
        if altitude is not None:
            result_key = FetcherKey.PRESSURE_REL
            item = FetcherItem(
                result_key,
                "AbsPress",
                transformation.RelPressureTransformation(result_key, FetcherKey.TEMP_OUTSIDE, altitude)
            )
            fetcher_items.append(item)

        return fetcher_items
