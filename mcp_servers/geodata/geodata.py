# geocoding_db.py
from typing import Any, List, Tuple
import sqlite3
from mcp.server.fastmcp import FastMCP
import math
from pathlib import Path

# Initialize FastMCP server
mcp = FastMCP("geodata")

# Constants
DEFAULT_DB_PATH = "cities.db"


def get_db_connection(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Get database connection with proper configuration."""
    if not Path(db_path).exists():
        raise FileNotFoundError(f"Database file '{db_path}' not found. Please run database_setup.py first.")
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Enable column access by name
    return conn


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points using Haversine formula (in kilometers)."""
    # Convert latitude and longitude from degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # Radius of earth in kilometers
    r = 6371
    return c * r


def format_city(city_row: sqlite3.Row) -> str:
    """Format a city row into a readable string."""
    pop_str = f"{city_row['pop']:,}" if city_row['pop'] else "Unknown"
    admin1_str = f", {city_row['admin1']}" if city_row['admin1'] else ""
    
    return f"""
Name: {city_row['name']}
Location: {city_row['name']}{admin1_str}, {city_row['country']}
Coordinates: {city_row['lat']}, {city_row['lon']}
Population: {pop_str}
ID: {city_row['id']}
"""


@mcp.tool()
async def search_cities(query: str, country: str = None, limit: int = 10) -> str:
    """Search for cities by name with optional country filter.

    Args:
        query: City name to search for (partial matches supported)
        country: Optional 2-letter country code filter (e.g., "US", "CN")
        limit: Maximum number of results (default: 10, max: 50)
    """
    limit = min(max(1, limit), 50)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Build query
        if country:
            country = country.upper()
            cursor.execute('''
                SELECT * FROM cities 
                WHERE name LIKE ? AND country = ?
                ORDER BY pop DESC NULLS LAST, name
                LIMIT ?
            ''', (f'%{query}%', country, limit))
        else:
            cursor.execute('''
                SELECT * FROM cities 
                WHERE name LIKE ?
                ORDER BY pop DESC NULLS LAST, name
                LIMIT ?
            ''', (f'%{query}%', limit))
        
        cities = cursor.fetchall()
        conn.close()
        
        if not cities:
            country_filter = f" in {country}" if country else ""
            return f"No cities found matching '{query}'{country_filter}."
        
        result = f"Found {len(cities)} cities matching '{query}':\n"
        result += "\n" + "="*50 + "\n".join([format_city(city) for city in cities])
        
        return result
        
    except FileNotFoundError as e:
        return f"Database error: {e}"
    except sqlite3.Error as e:
        return f"Database query error: {e}"


@mcp.tool()
async def get_city_by_id(city_id: str) -> str:
    """Get detailed information for a specific city by ID.

    Args:
        city_id: Unique city identifier
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM cities WHERE id = ?', (city_id,))
        city = cursor.fetchone()
        conn.close()
        
        if not city:
            return f"No city found with ID '{city_id}'."
        
        return f"City Details:\n{format_city(city)}"
        
    except FileNotFoundError as e:
        return f"Database error: {e}"
    except sqlite3.Error as e:
        return f"Database query error: {e}"


@mcp.tool()
async def find_cities_by_country(country: str, limit: int = 20) -> str:
    """Get all cities in a specific country, ordered by population.

    Args:
        country: 2-letter country code (e.g., "US", "CN", "FR")
        limit: Maximum number of cities to return (default: 20, max: 100)
    """
    limit = min(max(1, limit), 100)
    country = country.upper()
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM cities 
            WHERE country = ?
            ORDER BY pop DESC NULLS LAST, name
            LIMIT ?
        ''', (country, limit))
        
        cities = cursor.fetchall()
        conn.close()
        
        if not cities:
            return f"No cities found in country '{country}'."
        
        # Get total count
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM cities WHERE country = ?', (country,))
        total_count = cursor.fetchone()[0]
        conn.close()
        
        result = f"Top {len(cities)} cities in {country} (total: {total_count}):\n"
        result += "\n" + "="*50 + "\n".join([format_city(city) for city in cities])
        
        return result
        
    except FileNotFoundError as e:
        return f"Database error: {e}"
    except sqlite3.Error as e:
        return f"Database query error: {e}"


@mcp.tool()
async def find_nearby_cities(latitude: float, longitude: float, radius_km: float = 100, limit: int = 10) -> str:
    """Find cities within a specified radius of given coordinates.

    Args:
        latitude: Latitude of the center point
        longitude: Longitude of the center point
        radius_km: Search radius in kilometers (default: 100, max: 1000)
        limit: Maximum number of cities to return (default: 10, max: 50)
    """
    limit = min(max(1, limit), 50)
    radius_km = min(max(1, radius_km), 1000)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all cities (we'll filter by distance in Python for simplicity)
        # For large datasets, consider using spatial indexes or PostGIS
        cursor.execute('SELECT * FROM cities')
        all_cities = cursor.fetchall()
        conn.close()
        
        # Calculate distances and filter
        nearby_cities = []
        for city in all_cities:
            distance = calculate_distance(latitude, longitude, city['lat'], city['lon'])
            if distance <= radius_km:
                nearby_cities.append((city, distance))
        
        # Sort by distance
        nearby_cities.sort(key=lambda x: x[1])
        nearby_cities = nearby_cities[:limit]
        
        if not nearby_cities:
            return f"No cities found within {radius_km}km of coordinates ({latitude}, {longitude})."
        
        result = f"Found {len(nearby_cities)} cities within {radius_km}km of ({latitude}, {longitude}):\n"
        for city, distance in nearby_cities:
            result += f"\n{format_city(city)}"
            result += f"Distance: {distance:.2f} km\n"
            result += "="*50
        
        return result
        
    except FileNotFoundError as e:
        return f"Database error: {e}"
    except sqlite3.Error as e:
        return f"Database query error: {e}"


@mcp.tool()
async def get_largest_cities(limit: int = 20, country: str = None) -> str:
    """Get the largest cities by population.

    Args:
        limit: Number of cities to return (default: 20, max: 100)
        country: Optional country filter (2-letter code)
    """
    limit = min(max(1, limit), 100)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if country:
            country = country.upper()
            cursor.execute('''
                SELECT * FROM cities 
                WHERE country = ? AND pop IS NOT NULL
                ORDER BY pop DESC
                LIMIT ?
            ''', (country, limit))
        else:
            cursor.execute('''
                SELECT * FROM cities 
                WHERE pop IS NOT NULL
                ORDER BY pop DESC
                LIMIT ?
            ''', (limit,))
        
        cities = cursor.fetchall()
        conn.close()
        
        if not cities:
            country_filter = f" in {country}" if country else ""
            return f"No cities with population data found{country_filter}."
        
        country_title = f" in {country}" if country else " worldwide"
        result = f"Largest {len(cities)} cities by population{country_title}:\n"
        
        for i, city in enumerate(cities, 1):
            result += f"\n{i}. {format_city(city)}"
            result += "="*50 if i < len(cities) else ""
        
        return result
        
    except FileNotFoundError as e:
        return f"Database error: {e}"
    except sqlite3.Error as e:
        return f"Database query error: {e}"


@mcp.tool()
async def get_database_stats() -> str:
    """Get statistics about the cities database."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Total cities
        cursor.execute('SELECT COUNT(*) FROM cities')
        total_cities = cursor.fetchone()[0]
        
        # Countries
        cursor.execute('SELECT COUNT(DISTINCT country) FROM cities')
        total_countries = cursor.fetchone()[0]
        
        # Cities with population data
        cursor.execute('SELECT COUNT(*) FROM cities WHERE pop IS NOT NULL')
        cities_with_pop = cursor.fetchone()[0]
        
        # Top countries by city count
        cursor.execute('''
            SELECT country, COUNT(*) as city_count 
            FROM cities 
            GROUP BY country 
            ORDER BY city_count DESC 
            LIMIT 10
        ''')
        top_countries = cursor.fetchall()
        
        conn.close()
        
        result = f"""Database Statistics:
Total Cities: {total_cities:,}
Total Countries: {total_countries}
Cities with Population Data: {cities_with_pop:,}

Top 10 Countries by City Count:"""
        
        for country, count in top_countries:
            result += f"\n{country}: {count:,} cities"
        
        return result
        
    except FileNotFoundError as e:
        return f"Database error: {e}"
    except sqlite3.Error as e:
        return f"Database query error: {e}"


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')