

class RunnerConfKey:

    REFRESH_TIME = "refresh_time"
    RESILIENCE_TIME = "resilience_time"
    FETCH_TIMEOUT = "fetch_timeout"

    PAYLOAD_MQTT_TOPIC = "payload_mqtt_topic"
    PAYLOAD_MQTT_LAST_WILL = "payload_mqtt_last_will"

    SERVICE_MQTT_TOPIC = "service_mqtt_topic"
    SERVICE_MQTT_RUNNING = "service_mqtt_running"
    SERVICE_MQTT_STOPPED = "service_mqtt_stopped"


RUNNER_JSONSCHEMA = {
    "type": "object",
    "properties": {

        RunnerConfKey.RESILIENCE_TIME: {
            "type": "number",
            "minimum": 10,
            "description": "The service will tolerate errors within the resilience time (seconds). "
                           "After expiration the service will abort. But MQTT has to work initially."
        },
        RunnerConfKey.REFRESH_TIME: {
            "type": "number",
            "minimum": 10,
            "description": "Reloads are triggered after this time (seconds)."
        },
        RunnerConfKey.FETCH_TIMEOUT: {
            "type": "number",
            "minimum": 1,
            "description": "Timeout to fetch data (seconds)."
        },

        RunnerConfKey.PAYLOAD_MQTT_TOPIC: {
            "type": "string",
            "minLength": 1,
            "description": "Payload (data) MQTT topic."
        },
        RunnerConfKey.PAYLOAD_MQTT_LAST_WILL: {
            "type": "string",
            "minLength": 1,
            "description": "Payload (data) MQTT last will (leave empty to not set a las will)."
        },

        RunnerConfKey.SERVICE_MQTT_TOPIC: {
            "type": "string",
            "minLength": 1,
            "description": "Service (running/stopped) MQTT topic."
        },
        RunnerConfKey.SERVICE_MQTT_RUNNING: {
            "type": "string",
            "minLength": 1,
            "description": "Service (running/stopped) MQTT message, which is sent, when the service is started (running)."
        },
        RunnerConfKey.SERVICE_MQTT_STOPPED: {
            "type": "string",
            "minLength": 1,
            "description": "Service (running/stopped) MQTT message, which is sent, when the service is stopped (used as last will!)."
        },

    },
    "additionalProperties": False,
    "required": [RunnerConfKey.PAYLOAD_MQTT_TOPIC],
}
