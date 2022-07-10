

class RunnerConfKey:

    REFRESH_TIME = "refresh_time"
    RESILIENCE_TIME = "resilience_time"
    FETCH_TIMEOUT = "fetch_timeout"

    MQTT_OUTSIDE_TOPIC = "mqtt_outside_topic"
    MQTT_INSIDE_TOPIC = "mqtt_inside_topic"
    MQTT_LAST_WILL = "mqtt_last_will"


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

        RunnerConfKey.MQTT_OUTSIDE_TOPIC: {
            "type": "string",
            "minLength": 1,
            "description": "MQTT topic for outside weather station data"
        },
        RunnerConfKey.MQTT_INSIDE_TOPIC: {
            "type": "string",
            "minLength": 1,
            "description": "MQTT topic for inside sensor data."
        },
        RunnerConfKey.MQTT_LAST_WILL: {
            "type": "string",
            "minLength": 1,
            "description": "MQTT last will (leave empty to not set a las will)."
        },

    },
    "additionalProperties": False,
}
