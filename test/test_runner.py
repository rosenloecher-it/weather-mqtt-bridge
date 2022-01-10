import asyncio
import datetime
import json
import unittest
from typing import Optional
from unittest import mock
from unittest.mock import MagicMock, call

from src.fetcher.fetcher_factory import FetcherFactory
from src.fetcher.fetcher_key import FetcherKey
from src.fetcher.fetcher_result import FetcherStatus, FetcherResult
from src.runner import Runner
from src.runner_config import RunnerConfKey


class MockedFetcherFactory(FetcherFactory):

    def __init__(self, fetcher_job):
        super().__init__({})
        self.fetcher_job = fetcher_job

    def create_fetcher_job(self):
        return self.fetcher_job


class MockedRunner(Runner):

    def __init__(self, runner_config, fetcher_factory: FetcherFactory, mqtt_client):
        self.mock_now = None  # type: Optional[datetime.datetime]

        super().__init__(runner_config, fetcher_factory, mqtt_client)

    def run_wait_for_mqtt_connection_timeout(self, timeout):
        task = self._loop.create_task(self._wait_for_mqtt_connection_timeout(timeout))
        self._loop.run_until_complete(task)

    def fetch_data(self, timeout):
        task = self._loop.create_task(self._fetch_data_timeout(timeout))
        self._loop.run_until_complete(task)


class TestIntegration(unittest.TestCase):

    RESILIENCE_TIME = 75

    def setUp(self):
        self.fetcher_job = MagicMock()
        self.fetcher_factory = MockedFetcherFactory(self.fetcher_job)
        self.mqtt_client = MagicMock()

        self.runner_config = {
            RunnerConfKey.REFRESH_TIME: 30,
            RunnerConfKey.RESILIENCE_TIME: self.RESILIENCE_TIME,
            RunnerConfKey.PAYLOAD_MQTT_TOPIC: RunnerConfKey.PAYLOAD_MQTT_TOPIC,
            RunnerConfKey.PAYLOAD_MQTT_LAST_WILL: RunnerConfKey.PAYLOAD_MQTT_LAST_WILL,
            RunnerConfKey.SERVICE_MQTT_TOPIC: RunnerConfKey.SERVICE_MQTT_TOPIC,
            RunnerConfKey.SERVICE_MQTT_RUNNING: RunnerConfKey.SERVICE_MQTT_RUNNING,
            RunnerConfKey.SERVICE_MQTT_STOPPED: RunnerConfKey.SERVICE_MQTT_STOPPED,
        }

    def test_wait_for_mqtt_connection(self):
        call_counter = 0

        def is_connected():
            nonlocal call_counter
            call_counter += 1
            return False if call_counter < 3 else True

        self.mqtt_client.is_connected = is_connected

        runner = MockedRunner(self.runner_config, self.fetcher_factory, self.mqtt_client)
        runner.run_wait_for_mqtt_connection_timeout(100)

        self.assertEqual(call_counter, 3)

        self.mqtt_client.publish.assert_called_once_with(
            topic=RunnerConfKey.SERVICE_MQTT_TOPIC,
            payload=RunnerConfKey.SERVICE_MQTT_RUNNING
        )

    def test_wait_for_mqtt_connection_timeout(self):

        def is_connected():
            return False

        self.mqtt_client.is_connected = is_connected

        self.mqtt_client.is_connected = is_connected

        runner = MockedRunner(self.runner_config, self.fetcher_factory, self.mqtt_client)

        with self.assertRaises(asyncio.exceptions.TimeoutError):
            runner.run_wait_for_mqtt_connection_timeout(0.3)

    @mock.patch('src.time_utils.TimeUtils.now')
    def test_fetch(self, runner_now):
        time_fetch = datetime.datetime(2022, 1, 8, 10, 0, 0)
        time_result = datetime.datetime(2022, 1, 8, 10, 0, 2)

        fetcher_values = {"marker": 1234, FetcherKey.TIMESTAMP: time_fetch.isoformat()}
        fetcher_result = FetcherResult(status=FetcherStatus.OK, values=fetcher_values)

        self.mqtt_client.is_connected.return_value = True
        self.fetcher_job.fetch_safe.return_value = fetcher_result

        runner_now.return_value = time_fetch

        runner = MockedRunner(self.runner_config, self.fetcher_factory, self.mqtt_client)
        runner._start_fetcher_task()
        self.assertIsNotNone(runner._fetcher_task)

        runner.fetch_data(300)

        runner_now.return_value = time_result
        runner._handle_fetch_result()

        self.mqtt_client.publish.assert_called_once_with(
            topic=RunnerConfKey.PAYLOAD_MQTT_TOPIC,
            payload=json.dumps(fetcher_values, sort_keys=True)
        )
        self.mqtt_client.publish = MagicMock()  # reset

        runner.close()  # called via run.finally

        publish_calls = [
            call(topic=RunnerConfKey.PAYLOAD_MQTT_TOPIC, payload=RunnerConfKey.PAYLOAD_MQTT_LAST_WILL),
            call(topic=RunnerConfKey.SERVICE_MQTT_TOPIC, payload=RunnerConfKey.SERVICE_MQTT_STOPPED),
        ]
        self.mqtt_client.publish.assert_has_calls(publish_calls, any_order=True)

    @mock.patch('src.time_utils.TimeUtils.now')
    def test_fetch_timeout(self, mocked_now):

        time_fetch = datetime.datetime(2022, 1, 8, 10, 0, 0)
        time_not_yet_abort = datetime.datetime(2022, 1, 8, 10, 0, 0) + datetime.timedelta(seconds=self.RESILIENCE_TIME - 1)
        time_do_abort = datetime.datetime(2022, 1, 8, 10, 0, 0) + datetime.timedelta(seconds=self.RESILIENCE_TIME + 1)

        fetcher_values = {"marker": 12345, FetcherKey.TIMESTAMP: time_fetch.isoformat()}
        fetcher_result = FetcherResult(status=FetcherStatus.ERROR, values=fetcher_values)

        self.mqtt_client.is_connected.return_value = True
        self.fetcher_job.fetch_safe.return_value = fetcher_result

        mocked_now.return_value = time_fetch

        runner = MockedRunner(self.runner_config, self.fetcher_factory, self.mqtt_client)
        runner._handle_fetch_result()  # nothing to do

        # resilience period
        runner._start_fetcher_task()
        runner.fetch_data(300)

        mocked_now.return_value = time_not_yet_abort
        runner._handle_fetch_result()

        self.mqtt_client.publish.assert_called_once_with(
            topic=RunnerConfKey.PAYLOAD_MQTT_TOPIC,
            payload=json.dumps(fetcher_values, sort_keys=True)
        )
        self.mqtt_client.publish = MagicMock()  # reset

        # .. abort
        runner._start_fetcher_task()
        runner.fetch_data(300)

        mocked_now.return_value = time_do_abort

        with self.assertRaises(RuntimeError) as ex:
            runner._handle_fetch_result()

        self.assertTrue("abort" in str(ex.exception))

        self.mqtt_client.publish.assert_called_once_with(
            topic=RunnerConfKey.PAYLOAD_MQTT_TOPIC,
            payload=json.dumps(fetcher_values, sort_keys=True)
        )

        runner.close()  # called via run.finally

        publish_calls = [
            call(topic=RunnerConfKey.PAYLOAD_MQTT_TOPIC, payload=RunnerConfKey.PAYLOAD_MQTT_LAST_WILL),
            call(topic=RunnerConfKey.SERVICE_MQTT_TOPIC, payload=RunnerConfKey.SERVICE_MQTT_STOPPED),
        ]
        self.mqtt_client.publish.assert_has_calls(publish_calls, any_order=True)
