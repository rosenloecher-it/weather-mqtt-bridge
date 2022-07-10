import asyncio
import datetime
import logging
import signal
import threading
from asyncio import Task
from collections import namedtuple
from typing import Optional, List, Dict

from src.fetcher.fetcher_factory import FetcherFactory
from src.fetcher.fetcher_key import FetcherKey
from src.fetcher.fetcher_status import FetcherStatus
from src.runner_config import RunnerConfKey
from src.utils.json_utils import JsonUtils
from src.utils.time_utils import TimeUtils

_logger = logging.getLogger(__name__)


Message = namedtuple('Message', ['topic', 'payload'])  # status: FetcherStatus, values: Dict[str, any]


class Runner:

    DEFAULT_REFRESH_TIME = 60

    TIME_LIMIT_MQTT_CONNECTION = 10  # seconds

    def __init__(self, runner_config, fetcher_factory: FetcherFactory, mqtt_client):

        self._lock = threading.Lock()

        self._fetcher = None
        self._fetcher_factory = fetcher_factory

        self._refresh_time = runner_config.get(RunnerConfKey.REFRESH_TIME, self.DEFAULT_REFRESH_TIME)
        default_resilience_time = min(self._refresh_time * 2.2, 300)
        self._resilience_time = runner_config.get(RunnerConfKey.RESILIENCE_TIME, default_resilience_time)
        default_fetch_timeout = max(self._refresh_time / 2, 30)
        self._fetch_timeout = runner_config.get(RunnerConfKey.FETCH_TIMEOUT, default_fetch_timeout)

        self._payload_mqtt_last_will = runner_config.get(RunnerConfKey.MQTT_LAST_WILL)
        self._payload_mqtt_inside_topic = runner_config.get(RunnerConfKey.MQTT_INSIDE_TOPIC)
        self._payload_mqtt_outside_topic = runner_config.get(RunnerConfKey.MQTT_OUTSIDE_TOPIC)

        self._next_fetch_trigger = TimeUtils.now()
        # self._resilience_reference_time = TimeUtils.now()  # in combination with `self._resilience_time`

        self._mqtt_client = mqtt_client

        if self._payload_mqtt_last_will:
            if self._payload_mqtt_inside_topic:
                self._mqtt_client.set_last_will(self._payload_mqtt_inside_topic, self._payload_mqtt_last_will)
            if self._payload_mqtt_outside_topic and self._payload_mqtt_outside_topic != self._payload_mqtt_inside_topic:
                self._mqtt_client.set_last_will(self._payload_mqtt_outside_topic, self._payload_mqtt_last_will)

        self._mqtt_client.connect()

        self._loop = asyncio.get_event_loop()
        self._periodic_task = None  # type: Optional[Task]
        self._fetcher_task = None  # type: Optional[Task]
        self._fetcher_started = None  # type: Optional[datetime.datetime]

        if threading.current_thread() is threading.main_thread():
            # integration tests run the service in a thread...
            signal.signal(signal.SIGINT, self._shutdown_signaled)
            signal.signal(signal.SIGTERM, self._shutdown_signaled)

    def _shutdown_signaled(self, sig, _frame):
        _logger.info("shutdown signaled (%s)", sig)
        if self._periodic_task:
            self._periodic_task.cancel()

    def run(self):
        """endless loop"""
        self._periodic_task = self._loop.create_task(self._periodic())

        try:
            self._loop.run_until_complete(self._periodic_task)
        except asyncio.CancelledError:
            _logger.debug("canceling...")
        finally:
            self.close()

    async def _wait_for_mqtt_connection_timeout(self, timeout):
        try:
            return await asyncio.wait_for(self._wait_for_mqtt_connection(), timeout)
        except asyncio.exceptions.TimeoutError:
            raise asyncio.exceptions.TimeoutError(f"couldn't connect to MQTT (within {timeout}s)!") from None

    async def _wait_for_mqtt_connection(self):
        while True:
            if self._mqtt_client.is_connected():
                break

            await asyncio.sleep(0.1)

    async def _periodic(self):
        await self._wait_for_mqtt_connection_timeout(self.TIME_LIMIT_MQTT_CONNECTION)

        while True:
            self._handle_fetch_result()

            if TimeUtils.now() >= self._next_fetch_trigger:
                self._start_fetcher_task()
            else:
                self._mqtt_client.ensure_connection()

            await asyncio.sleep(0.1)

    def _start_fetcher_task(self):
        if self._fetcher_task:
            now = TimeUtils.now()
            running_time = (self._fetcher_started - now).total_seconds() if self._fetcher_started else None
            if running_time is not None and running_time < self._fetch_timeout:
                _logger.warning("fetcher task not finished - wrong (?) timing: running=%.1fs; timeout=%.1fs; refresh=%.1fs",
                                running_time, self._fetch_timeout, self._refresh_time)
                return
            raise RuntimeError("fetcher task not finished!")

        self._fetcher_task = self._loop.create_task(self._fetch_data_timeout())  # type: Task
        self._fetcher_started = TimeUtils.now()

    async def _fetch_data_timeout(self, timeout=None):
        timeout = timeout or self._fetch_timeout
        try:
            return await asyncio.wait_for(self._fetch_data(), timeout or self._fetch_timeout)
        except asyncio.exceptions.TimeoutError:
            _logger.error("timeout (%.1fs) fetching data", timeout)
            return {FetcherKey.STATUS: FetcherStatus.TIMEOUT}

    async def _fetch_data(self):
        self._next_fetch_trigger = TimeUtils.now() + datetime.timedelta(seconds=self._refresh_time)
        _logger.debug("_fetch_data...")

        fetcher = self._fetcher_factory.create_fetcher_job()
        return fetcher.fetch_safe()

    def _handle_fetch_result(self):
        if not self._fetcher_task or not self._fetcher_task.done():
            return

        fetcher_values = self._fetcher_task.result()
        self._fetcher_task = None
        self._fetcher_started = None

        _logger.debug("fetch_result: %s", fetcher_values)

        messages = self.splitt_messages(
            fetcher_values,
            outside_topic=self._payload_mqtt_outside_topic,
            inside_topic=self._payload_mqtt_inside_topic,
        )

        for message in messages:
            self._mqtt_client.publish(topic=message.topic, payload=message.payload)

    def close(self):
        if self._mqtt_client is not None:
            try:
                if self._payload_mqtt_last_will:
                    if self._payload_mqtt_inside_topic:
                        self._mqtt_client.publish(topic=self._payload_mqtt_inside_topic, payload=self._payload_mqtt_last_will)
                    if self._payload_mqtt_outside_topic and self._payload_mqtt_inside_topic != self._payload_mqtt_outside_topic:
                        self._mqtt_client.publish(topic=self._payload_mqtt_outside_topic, payload=self._payload_mqtt_last_will)

            except Exception as ex:
                _logger.error("could not publish the final service messages! %s", ex)

            self._mqtt_client = None

    @classmethod
    def splitt_messages(cls, fetcher_values: Optional[Dict[str, any]], inside_topic: str, outside_topic: str) -> List[Message]:
        messages = []

        fetcher_values = {} if fetcher_values is None else fetcher_values

        source_timestamp = fetcher_values.get(FetcherKey.TIMESTAMP) or TimeUtils.now().isoformat()
        if isinstance(source_timestamp, datetime.datetime):
            source_timestamp = source_timestamp.isoformat()

        def append_value(values_out, key_in, key_out=None):
            if key_out is None:
                key_out = key_in
            value = fetcher_values.get(key_in)
            if value is not None:
                values_out[key_out] = value

        def add_meta(values_, sensor_name):
            status = fetcher_values.get(FetcherKey.STATUS) or FetcherStatus.ERROR
            if status == FetcherStatus.OK and not values_:
                status = FetcherStatus.ERROR
            values_[FetcherKey.STATUS] = status
            values_[FetcherKey.TIMESTAMP] = source_timestamp
            values_[FetcherKey.SENSOR] = sensor_name

        if inside_topic:
            values = {}
            append_value(values, FetcherKey.BATTERY_INSIDE, FetcherKey.BATTERY)
            append_value(values, FetcherKey.HUMI_INSIDE, FetcherKey.HUMI)
            append_value(values, FetcherKey.TEMP_INSIDE, FetcherKey.TEMP)
            add_meta(values, "inside1")

            message = Message(inside_topic, JsonUtils.dumps(values))
            messages.append(message)

        if outside_topic:
            values = {}
            append_value(values, FetcherKey.PRESSURE_ABS)
            append_value(values, FetcherKey.PRESSURE_REL)
            append_value(values, FetcherKey.WIND_DIRECTION)
            append_value(values, FetcherKey.WIND_GUST)
            append_value(values, FetcherKey.WIND_SPEED)
            append_value(values, FetcherKey.SOLAR_RADIATION)
            append_value(values, FetcherKey.UVI)
            append_value(values, FetcherKey.RAIN_HOURLY)
            append_value(values, FetcherKey.RAIN_COUNTER)

            append_value(values, FetcherKey.BATTERY_OUTSIDE, FetcherKey.BATTERY)
            append_value(values, FetcherKey.HUMI_OUTSIDE, FetcherKey.HUMI)
            append_value(values, FetcherKey.TEMP_OUTSIDE, FetcherKey.TEMP)

            add_meta(values, "weatherStation")

            message = Message(outside_topic, JsonUtils.dumps(values))
            messages.append(message)

        return messages
