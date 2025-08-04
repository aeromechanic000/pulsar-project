from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP
import urllib.parse

# Initialize FastMCP server
mcp = FastMCP("geocoding")

# Constants
NOMINATIM_API_BASE = "https://nominatim.openstreetmap.org"
USER_AGENT = "geocoding-app/1.0"


async def make_nominatim_request(url: str) -> list[dict[str, Any]] | None:
    """Make a request to the Nominatim API with proper error handling."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json"
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception:
            return None


def format_location(location_data: dict) -> str:
    """Format a location data into a readable string."""
    lat = location_data.get('lat', 'Unknown')
    lon = location_data.get('lon', 'Unknown')
    name = location_data.get('name', 'Unknown')
    display_name = location_data.get('display_name', 'Unknown')
    place_rank = location_data.get('place_rank', 'Unknown')
    importance = location_data.get('importance', 'Unknown')
    address_type = location_data.get('addresstype', 'Unknown')
    
    return f"""
Name: {name}
Display Name: {display_name}
Latitude: {lat}
Longitude: {lon}
Address Type: {address_type}
Place Rank: {place_rank}
Importance: {importance}
"""


@mcp.tool()
async def search_location(query: str, limit: int = 5) -> str:
    """Search for a location and get its coordinates using Nominatim API.

    Args:
        query: City name or location to search for (e.g., "Beijing", "Los Angeles", "LA")
        limit: Maximum number of results to return (default: 5, max: 10)
    """
    # Limit the number of results to prevent excessive data
    limit = min(max(1, limit), 10)
    
    # URL encode the query to handle special characters and spaces
    encoded_query = urllib.parse.quote(query)
    url = f"{NOMINATIM_API_BASE}/search?format=json&q={encoded_query}&limit={limit}"
    
    data = await make_nominatim_request(url)

    if not data:
        return f"Unable to fetch location data for '{query}'. Please check your internet connection or try again later."

    if not data:
        return f"No locations found for '{query}'. Please try a different search term."

    # Format all results
    locations = [format_location(location) for location in data]
    result = f"Found {len(locations)} location(s) for '{query}':\n"
    result += "\n" + "="*50 + "\n".join(locations)
    
    return result


@mcp.tool()
async def get_coordinates(query: str) -> str:
    """Get the coordinates (latitude and longitude) for the most relevant location.

    Args:
        query: City name or location to search for (e.g., "Beijing", "Los Angeles")
    """
    # URL encode the query
    encoded_query = urllib.parse.quote(query)
    url = f"{NOMINATIM_API_BASE}/search?format=json&q={encoded_query}&limit=1"
    
    data = await make_nominatim_request(url)

    if not data:
        return f"Unable to fetch coordinates for '{query}'. Please check your internet connection or try again later."

    if not data:
        return f"No location found for '{query}'. Please try a different search term."

    location = data[0]
    lat = location.get('lat', 'Unknown')
    lon = location.get('lon', 'Unknown')
    display_name = location.get('display_name', 'Unknown')
    
    return f"""
Location: {display_name}
Latitude: {lat}
Longitude: {lon}
"""


@mcp.tool()
async def search_location_detailed(query: str, country_code: str = None, limit: int = 3) -> str:
    """Search for a location with optional country filtering and get detailed information.

    Args:
        query: City name or location to search for
        country_code: Optional 2-letter country code to filter results (e.g., "US", "CN", "FR")
        limit: Maximum number of results to return (default: 3, max: 10)
    """
    # Limit the number of results
    limit = min(max(1, limit), 10)
    
    # URL encode the query
    encoded_query = urllib.parse.quote(query)
    url = f"{NOMINATIM_API_BASE}/search?format=json&q={encoded_query}&limit={limit}&addressdetails=1"
    
    # Add country code filter if provided
    if country_code:
        country_code = country_code.upper()
        url += f"&countrycodes={country_code}"
    
    data = await make_nominatim_request(url)

    if not data:
        return f"Unable to fetch location data for '{query}'. Please check your internet connection or try again later."

    if not data:
        country_filter = f" in {country_code}" if country_code else ""
        return f"No locations found for '{query}'{country_filter}. Please try a different search term."

    # Format results with more details
    locations = []
    for location in data:
        lat = location.get('lat', 'Unknown')
        lon = location.get('lon', 'Unknown')
        name = location.get('name', 'Unknown')
        display_name = location.get('display_name', 'Unknown')
        place_rank = location.get('place_rank', 'Unknown')
        importance = location.get('importance', 'Unknown')
        address_type = location.get('addresstype', 'Unknown')
        osm_type = location.get('osm_type', 'Unknown')
        
        location_info = f"""
Name: {name}
Full Address: {display_name}
Coordinates: {lat}, {lon}
Type: {address_type}
Place Rank: {place_rank}
Importance: {importance:.4f}
OSM Type: {osm_type}
"""
        locations.append(location_info)
    
    country_filter = f" in {country_code}" if country_code else ""
    result = f"Found {len(locations)} detailed location(s) for '{query}'{country_filter}:\n"
    result += "\n" + "="*60 + "\n".join(locations)
    
    return result


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')