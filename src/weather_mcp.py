# src/servers/weather_mcp.py

"""Utility module for fetching weather data from OpenWeatherMap.

Provides a simple function :func:`get_weather` that returns the JSON response
from the OpenWeatherMap *Current Weather Data* endpoint.
"""

import json
import os
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional
from fastmcp import FastMCP
from dotenv import load_dotenv
import os

load_dotenv()  # Load environment variables from .env file

# Create the FastMCP server
mcp = FastMCP("weather-server")

@mcp.tool()
def get_weather(city: str, api_key: Optional[str] = None) -> Dict[str, Any]:
    """Fetch current weather for *city* from OpenWeatherMap.

    The function reads the API key from the ``OPEN_WEATHER_MAP_API_KEY``
    environment variable unless an explicit ``api_key`` argument is supplied.

    Args:
        city: City name to query, e.g. ``"London"``.
        api_key: Optional explicit API key; if omitted the environment variable
            is used.

    Returns:
        The parsed JSON response as a ``dict``.

    Raises:
        ValueError: If no API key is available.
        urllib.error.HTTPError: For HTTP errors returned by the API.
    """
    if api_key is None:
        api_key = os.getenv("OPEN_WEATHER_MAP_API_KEY")
    if not api_key:
        raise ValueError("OpenWeatherMap API key not set in environment")

    base_url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city,
        "appid": api_key,
        "units": "metric",
    }
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url) as response:
        # The response is JSON; decode to dict
        return json.load(response)


if __name__ == "__main__":
    mcp.run(transport="http", port=8000)