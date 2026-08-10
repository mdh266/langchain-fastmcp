import json
import os
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional
from fastmcp import FastMCP
from dotenv import load_dotenv
import os
from typing import Dict, Optional
import googlemaps
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point


load_dotenv()  # Load environment variables from .env file

# Create the FastMCP server
mcp = FastMCP("all-server")


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


@mcp.tool()
def convert_address_to_point(address: str ) -> Dict[str, float]:
    """
    Convert a street address to a Shapely Point object.

    Parameters
    ----------
    address: str
        A free‑form US address (e.g. ``"123 Main St, New York, NY 10001"``).

    Returns
    -------
    Dict[str, float]
        A dictionary containing the longitude and latitude of the address.
        Returns None if the geocoding request fails.

    Example
    -------
    >> convert_address_to_point("123 Main St, New York, NY 10001")
    {'lng': -73.985428, 'lat': 40.748817}
    """
    gmaps = googlemaps.Client(key=os.getenv("GOOGLE_API_KEY"))
    location = gmaps.geocode(address)
    if not location:
        return None
    point = location[0].get("geometry").get("location")
    return point


@mcp.tool()
def get_police_precinct(lat_longs: Dict[str, float]) -> int:
    """
    Resolve a street address to the NYPD precinct number.

    This tool is exposed via the FastMCP server, so it can be called
    directly from a Claude Code agent or from the HTTP / MCP endpoint.

    Parameters
    ----------
    lat_longs: Dict[str, float]
        A dictionary containing the latitude and longitude of the location.

    Returns
    -------
    int or None
        The precinct identifier (the ``pct`` column from the NYPD sector
        shapefile).  Returns ``None`` when the address does not intersect
        any precinct polygon or when the geocoding request fails.

    Example
    -------
    >> get_police_precinct({"lat": 40.748817, "lng": -73.985428})
    19
    """
    df = gpd.read_parquet("NYPD_Sectors_20260507.parquet")
    geo_point = Point(lat_longs.get("lng"), lat_longs.get("lat"))
    precinct = df[df["geometry"].contains(geo_point)][["pct", "sector"]]
    return int(precinct.iloc[0]["pct"]) if not precinct.empty else None


@mcp.tool()
def get_precinct_info(precinct_number: int) -> Dict[str, str]:
    """
    Return the precinct information for a given precinct number.

    Parameters
    ----------
    precinct_number: int
        The precinct number (e.g. 1, 5, 14, etc.).

    Returns
    -------
    dict
        A dictionary containing the precinct information (e.g. name, address, etc.).
        Returns an empty dictionary if the pre
    df = pd.read_parquet("precinct_info.parquet")
    precinct_info = df[df["precinct_number"] == precinct_number].to_dict(orient="records")
    return precinct_info[0] if precinct_info else {}
cinct number is not found.
    """
    df = pd.read_parquet("precinct_info.parquet")
    precinct_info = df[df["precinct_number"] == precinct_number].to_dict(orient="records")
    return precinct_info[0] if precinct_info else {}


if __name__ == "__main__":
    mcp.run(transport="http", port=8000)