#!/usr/bin/env python3
import logging
import sys
from typing import Optional

import click

from src.app_config import AppConfig
from src.app_logging import AppLogging, LOGGING_CHOICES
from src.fetcher.fetcher_factory import FetcherFactory
from src.mqtt_client import MqttClient
from src.runner import Runner


_logger = logging.getLogger(__name__)


@click.command()
@click.option(
    "--json-schema",
    is_flag=True,
    help="Prints the config file JSON schema and exits."
)
@click.option(
    "--config-file",
    default="/etc/froggit-mqtt-logger.yaml",
    help="Config file",
    show_default=True,
    # type=click.Path(exists=True),
)
@click.option(
    "--log-file",
    help="Log file (if stated journal logging is disabled)"
)
@click.option(
    "--log-level",
    help="Log level",
    type=click.Choice(LOGGING_CHOICES, case_sensitive=False),
)
@click.option(
    "--print-logs",
    is_flag=True,
    help="Prints log output to console too"
)
@click.option(
    "--systemd-mode",
    is_flag=True,
    help="Systemd/journald integration: skip timestamp + prints to console"
)
def _main(json_schema, config_file, log_file, log_level, print_logs, systemd_mode):
    try:
        if json_schema:
            AppConfig.print_config_file_json_schema()
        else:
            run_service(config_file, log_file, log_level, print_logs, systemd_mode)

    except KeyboardInterrupt:
        pass

    except Exception as ex:
        _logger.exception(ex)
        sys.exit(1)  # a simple return is not understood by click


def run_service(config_file, log_file, log_level, print_logs, systemd_mode):
    """Logs MQTT messages to a Postgres database."""

    runner = None  # type: Optional[Runner]

    mqtt_client = None
    # self._mqtt = MqttClient(app_config.get_mqtt_config())

    try:
        app_config = AppConfig(config_file)
        AppLogging.configure(
            app_config.get_logging_config(),
            log_file, log_level, print_logs, systemd_mode
        )

        _logger.debug("start")

        runner_config = app_config.get_runner_config()
        fetcher_factoy = FetcherFactory(app_config.get_fetcher_config())
        mqtt_client = MqttClient(app_config.get_mqtt_config())

        runner = Runner(runner_config, fetcher_factoy, mqtt_client)
        runner.run()

    finally:
        _logger.info("shutdown")
        if runner is not None:
            runner.close()
        if mqtt_client is not None:
            mqtt_client.close()


if __name__ == '__main__':
    _main()  # exit codes must be handled by click!
