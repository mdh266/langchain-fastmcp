import json
import os
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional
from fastmcp import FastMCP
from dotenv import load_dotenv, find_dotenv
from typing import Dict, Optional
import googlemaps
import redis
from utils import get_mongo_client


load_dotenv(find_dotenv())  # Load environment variables from .env file

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


@mcp.tool(
      name="get_police_precinct",
      description="Resolve a street address to the NYPD precinct number."
)
def get_police_precinct(point: Dict[str, float]) -> int | None:
    """
    Resolve a street address to the NYPD precinct number.

    This tool is exposed via the FastMCP server, so it can be called
    directly from a Claude Code agent or from the HTTP / MCP endpoint.

    Parameters
    ----------
    point: Dict[str, float]
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
    client = get_mongo_client()

    query = {"geom": { 
            "$geoIntersects": { 
                "$geometry": { 
                "type": "Point", 
                "coordinates": [ point.get("lng"), point.get("lat")]
                            } 
                    } 
            } 
    } 

    projection = {"_id":0, "precinct_number":1}

    precinct_info =  (client.get_database("nyc")
                            .get_collection("precincts")
                            .find_one(query, projection))

    return int(precinct_info.get("precinct_number")) if precinct_info else None


@mcp.tool(
    name="find_closest_restroom",
    description="Find the closest public restroom to a given point and all information on it",
    output_schema={  # a free‑form schema – essentially “anything”
    "type": "object",
    "additionalProperties": True,
})
def find_closest_restroom(point: Dict[str, float]) -> Dict[str, Any]:
    """
    Find the closest public restroom to a given point.

    Parameters
    ----------
    point: Dict[str, float]
    
        A dictionary containing the latitude and longitude of the location to search from.

    Returns
    -------
    dict
        A dictionary containing the information of the closest restroom.
        Returns an empty dictionary if no restrooms are found.
    """
    client = get_mongo_client()
    collection = client.get_database("nyc").get_collection("restrooms")
    pipeline = [
        {
            "$geoNear": {
                "near": {"type": "Point", "coordinates": [point.get("lng"), point.get("lat")]},
                "distanceField": "calculated_distance",
                "spherical": True,
                "key": "geom"
            }
        },
        {"$limit": 1}
    ]

    results = list(collection.aggregate(pipeline))
    values = {}
    if len(results) > 0: 
        # Copy a predefined set of fields from the Mongo result into the response dict
        _fields = [
            "facility_name",
            "location_type",
            "operator",
            "status",
            "open",
            "hours_of_operation",
            "accessibility",
            "restroom_type",
            "changing_stations",
            "latitude",
            "longitude",
        ]
        for _k in _fields:
            values[_k] = results[0].get(_k)
        values["website"] = results[0].get("website").get("url")
    return values
    

@mcp.tool(
    name="get_precinct_info",
    description="Return the precinct information for a given precinct number."
)
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
  
    """
    r = redis.Redis(
        host=os.getenv("REDIS_HOST"),
        port=11170,
        decode_responses=True,
        username=os.getenv("REDIS_USERNAME"),
        password=os.getenv("REDIS_PASSWORD")
    )
    try:
        result = r.get(str(precinct_number))
        if result:
            return json.loads(result)
    except Exception as e:
        print(f"Error fetching precinct info for {precinct_number}: {e}")

    return {}  # Return an empty dict if no info is found

if __name__ == "__main__":
    mcp.run(transport="http", port=8000)