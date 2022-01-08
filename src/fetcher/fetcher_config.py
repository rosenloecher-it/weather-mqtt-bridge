
class FetcherConfKey:
    URL = "url"
    ALTITUDE = "altitude"


FETCHER_JSONSCHEMA = {
    "type": "object",
    "properties": {

        FetcherConfKey.ALTITUDE: {
            "type": "number",
            "minimum": -1000,
            "maximum": 10000,
            "description": "Altitude is used to calculate the relative pressure."
        },


        FetcherConfKey.URL: {
            "type": "string",
            "minLength": 1,
            "description": "URL to download the weather data."
        },

    },
    "additionalProperties": False,
    "required": [FetcherConfKey.URL],
}
