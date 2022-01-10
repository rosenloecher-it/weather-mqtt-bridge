import asyncio
import datetime
import json
import logging
import signal
import threading
from asyncio import Task
from typing import Optional

from src.fetcher.fetcher_factory import FetcherFactory
from src.fetcher.fetcher_key import FetcherKey
from src.fetcher.fetcher_result import FetcherStatus, FetcherResult
from src.mqtt_client import MqttException
from src.runner_config import RunnerConfKey
from src.time_utils import TimeUtils

_logger = logging.getLogger(__name__)


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

        self._payload_mqtt_last_will = runner_config.get(RunnerConfKey.PAYLOAD_MQTT_LAST_WILL)
        self._payload_mqtt_topic = runner_config[RunnerConfKey.PAYLOAD_MQTT_TOPIC]
        self._service_mqtt_running = runner_config.get(RunnerConfKey.SERVICE_MQTT_RUNNING)
        self._service_mqtt_stopped = runner_config.get(RunnerConfKey.SERVICE_MQTT_STOPPED)  # == last will
        self._service_mqtt_topic = runner_config.get(RunnerConfKey.SERVICE_MQTT_TOPIC)

        self._next_fetch_trigger = TimeUtils.now()
        self._resilience_reference_time = TimeUtils.now()  # in combination with `self._resilience_time`

        self._mqtt_client = mqtt_client

        if self._payload_mqtt_last_will:
            self._mqtt_client.set_last_will(self._payload_mqtt_topic, self._payload_mqtt_last_will)
        if self._service_mqtt_stopped and self._service_mqtt_topic:
            self._mqtt_client.set_last_will(self._service_mqtt_topic, self._service_mqtt_stopped)

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
                if self._service_mqtt_running and self._service_mqtt_topic:
                    self._mqtt_client.publish(topic=self._service_mqtt_topic, payload=self._service_mqtt_running)
                break

            await asyncio.sleep(0.1)

    async def _periodic(self):
        await self._wait_for_mqtt_connection_timeout(self.TIME_LIMIT_MQTT_CONNECTION)

        while True:
            self._handle_fetch_result()

            if TimeUtils.now() >= self._next_fetch_trigger:
                self._start_fetcher_task()

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
            return FetcherResult(FetcherStatus.TIMEOUT, {})

    async def _fetch_data(self):
        self._next_fetch_trigger = TimeUtils.now() + datetime.timedelta(seconds=self._refresh_time)
        _logger.debug("_fetch_data...")

        fetcher = self._fetcher_factory.create_fetcher_job()
        fetch_result = fetcher.fetch_safe()
        # await asyncio.sleep(1)  # 1.1
        # result = FetcherResult(FetcherStatus.SUCCESS, {"reason": "better"})

        return fetch_result

    def _handle_fetch_result(self):
        if not self._fetcher_task or not self._fetcher_task.done():
            return

        fetcher_result = self._fetcher_task.result()
        self._fetcher_task = None
        self._fetcher_started = None

        _logger.debug("fetch_result: %s", fetcher_result)

        fetcher_status = fetcher_result.status or FetcherStatus.ERROR
        fetcher_values = fetcher_result.values or {}

        fetcher_values[FetcherKey.STATUS] = fetcher_status
        if not fetcher_values.get(FetcherKey.TIMESTAMP):
            fetcher_values[FetcherKey.TIMESTAMP] = TimeUtils.now().isoformat()

        message = json.dumps(fetcher_values, sort_keys=True)
        within_resilience_period = (TimeUtils.now() - self._resilience_reference_time).total_seconds() <= self._resilience_time

        sent_message_failure = False
        try:
            self._mqtt_client.publish(topic=self._payload_mqtt_topic, payload=message)
        except MqttException:
            if within_resilience_period:
                _logger.error("MQTT publish failed. But errors within resilience period are tolerated!", exc_info=True)
                sent_message_failure = True
            else:
                raise

        if fetcher_status == FetcherStatus.OK and not sent_message_failure:
            self._resilience_reference_time = TimeUtils.now()

        if fetcher_status != FetcherStatus.OK:
            if within_resilience_period:
                _logger.warning("fetcher error (%s) within resilience period!", str(fetcher_result.status))
            else:
                raise RuntimeError(f"fetcher error ({fetcher_result.status}) => abort!")

    def close(self):
        if self._mqtt_client is not None:
            try:
                if self._payload_mqtt_last_will:
                    self._mqtt_client.publish(topic=self._payload_mqtt_topic, payload=self._payload_mqtt_last_will)
                if self._service_mqtt_stopped and self._service_mqtt_topic:
                    self._mqtt_client.publish(topic=self._service_mqtt_topic, payload=self._service_mqtt_stopped)
            except Exception as ex:
                _logger.error("could not publish the final service messages! %s", ex)

            self._mqtt_client = None
