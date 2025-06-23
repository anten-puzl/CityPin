import os
from pathlib import Path
import pandas as pd
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import requests
import time
from urllib.parse import quote
import json
import math

# Global dictionary for caching coordinate query results
location_cache = {}

# Function to load cache from file
def load_cache_from_file():
    """Loads coordinate cache from file"""
    cache_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'location_cache.json')
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                # Load cache from file
                cache_data = json.load(f)
                # Convert keys back to strings (they were saved as strings)
                return cache_data
        except Exception as e:
            print(f"Error loading cache from file: {e}")
    return {}

# Function to save cache to file
def save_cache_to_file(cache):
    """Saves coordinate cache to file"""
    cache_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'location_cache.json')
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            # Save cache to file in JSON format
            json.dump(cache, f, ensure_ascii=False, indent=2)
        print(f"Cache saved to file: {cache_file}")
    except Exception as e:
        print(f"Error saving cache to file: {e}")

# Function to check if coordinates are close
def are_coordinates_close(lat1, lon1, lat2, lon2, threshold=0.01):
    """Checks if coordinates are close enough to each other"""
    # Check if the difference between coordinates is less than the threshold
    # 0.01 degrees is approximately 1 km at the equator
    return abs(lat1 - lat2) < threshold and abs(lon1 - lon2) < threshold

# Function to find close coordinates in cache
def find_in_cache(latitude, longitude):
    """Searches for close coordinates in cache"""
    if latitude is None or longitude is None:
        return None
    
    # Round coordinates to 6 decimal places for comparison
    lat_rounded = round(latitude, 6)
    lon_rounded = round(longitude, 6)
    
    # Check for exact match
    cache_key = f"{lat_rounded},{lon_rounded}"
    if cache_key in location_cache:
        print(f"Using cached data for coordinates: {cache_key}")
        return location_cache[cache_key]
    
    # If no exact match, look for close coordinates
    for key in location_cache.keys():
        try:
            # Split key into coordinates
            cached_lat, cached_lon = map(float, key.split(','))
            
            # Check if coordinates are close enough
            if are_coordinates_close(lat_rounded, lon_rounded, cached_lat, cached_lon):
                print(f"Using cached data for close coordinates: {key} (requested: {lat_rounded},{lon_rounded})")
                return location_cache[key]
        except Exception as e:
            # Skip invalid keys
            continue
    
    # If nothing found
    return None

# Function to convert GPS coordinates from EXIF format to decimal degrees
def convert_to_degrees(value):
    """Converts GPS coordinates from EXIF format to decimal degrees"""
    d = float(value[0])
    m = float(value[1])
    s = float(value[2])
    return d + (m / 60.0) + (s / 3600.0)

# Function to get GPS coordinates from EXIF data
def get_gps_info(exif_data):
    """Extracts GPS information from EXIF data"""
    if not exif_data:
        return None
    
    gps_info = {}
    
    # Look for GPS data in EXIF
    for key, value in exif_data.items():
        tag_name = TAGS.get(key, key)
        if tag_name == 'GPSInfo':
            # Process GPS data
            for gps_key in value:
                sub_tag_name = GPSTAGS.get(gps_key, gps_key)
                gps_info[sub_tag_name] = value[gps_key]
    
    # Check for necessary GPS data
    if 'GPSLatitude' in gps_info and 'GPSLongitude' in gps_info:
        lat = convert_to_degrees(gps_info['GPSLatitude'])
        # Consider direction (N/S)
        if gps_info.get('GPSLatitudeRef', 'N') == 'S':
            lat = -lat
            
        lon = convert_to_degrees(gps_info['GPSLongitude'])
        # Consider direction (E/W)
        if gps_info.get('GPSLongitudeRef', 'E') == 'W':
            lon = -lon
            
        return {'latitude': lat, 'longitude': lon}
    
    return None

# Function to determine city by GPS coordinates
def get_location_info(latitude, longitude):
    """Gets location information by GPS coordinates using Nominatim API with caching"""
    if latitude is None or longitude is None:
        return None
    
    # Look for close coordinates in cache
    cached_result = find_in_cache(latitude, longitude)
    if cached_result:
        return cached_result
    
    # Round coordinates to 6 decimal places for caching
    lat_rounded = round(latitude, 6)
    lon_rounded = round(longitude, 6)
    
    # Create cache key
    cache_key = f"{lat_rounded},{lon_rounded}"
    
    # Form URL for Nominatim API request
    url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={latitude}&lon={longitude}&zoom=10&addressdetails=1"
    
    # Add User-Agent to headers (Nominatim API requirement)
    headers = {
        'User-Agent': 'CityPin/1.0 (https://github.com/yourusername/citypin)'
    }
    
    try:
        # Send request
        response = requests.get(url, headers=headers)
        
        # Check request success
        if response.status_code == 200:
            data = response.json()
            
            # Extract location information
            location_info = {
                'city': None,
                'state': None,
                'country': None,
                'display_name': data.get('display_name')
            }
            
            # Get detailed address information
            address = data.get('address', {})
            
            # Try to get city (may be in different fields)
            location_info['city'] = address.get('city') or address.get('town') or \
                                   address.get('village') or address.get('hamlet') or \
                                   address.get('municipality')
            
            # Get region/state
            location_info['state'] = address.get('state') or address.get('region') or \
                                    address.get('province') or address.get('county')
            
            # Get country
            location_info['country'] = address.get('country')
            
            # Save result to cache
            location_cache[cache_key] = location_info
            
            return location_info
        else:
            print(f"Error in Nominatim API request: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error determining location: {e}")
        return None

# Function to scan directory with photos
def scan_photos_directory(directory):
    """Scans specified directory and extracts GPS coordinates from photos"""
    # Supported image formats
    supported_formats = ('.jpg', '.jpeg', '.tiff', '.png')
    
    # Create list to store data
    photo_data = []
    
    # Recursively traverse all files in specified directory
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(supported_formats):
                file_path = os.path.join(root, file)
                try:
                    # Open image
                    with Image.open(file_path) as img:
                        # Get EXIF data
                        exif_data = img._getexif()
                        
                        # Extract GPS information
                        gps_info = get_gps_info(exif_data)
                        
                        # If GPS information found, add to list
                        if gps_info:
                            photo_data.append({
                                'file_path': file_path,
                                'latitude': gps_info['latitude'],
                                'longitude': gps_info['longitude']
                            })
                        else:
                            # If GPS information not found, add entry without coordinates
                            photo_data.append({
                                'file_path': file_path,
                                'latitude': None,
                                'longitude': None
                            })
                except Exception as e:
                    print(f"Error processing file {file_path}: {e}")
    
    # Create DataFrame from collected data
    df = pd.DataFrame(photo_data)
    return df

# Function to add location information to photo data
def add_location_info(photos_df):
    """Adds location information to DataFrame with photo data"""
    # Add new columns for location information
    photos_df['city'] = None
    photos_df['state'] = None
    photos_df['country'] = None
    photos_df['display_name'] = None
    
    # Counter for processed photos with coordinates
    processed_count = 0
    total_with_coords = photos_df['latitude'].notna().sum()
    
    # Process each row with coordinates
    for index, row in photos_df[photos_df['latitude'].notna()].iterrows():
        processed_count += 1
        print(f"Determining location for photo {processed_count}/{total_with_coords}: {row['file_path']}")
        
        # Get location information
        location_info = get_location_info(row['latitude'], row['longitude'])
        
        # If information obtained, add it to DataFrame
        if location_info:
            photos_df.at[index, 'city'] = location_info['city']
            photos_df.at[index, 'state'] = location_info['state']
            photos_df.at[index, 'country'] = location_info['country']
            photos_df.at[index, 'display_name'] = location_info['display_name']
        
        # Pause between requests to not exceed Nominatim API limit
        # If data was retrieved from cache, no pause needed
        if not find_in_cache(row['latitude'], row['longitude']):
            time.sleep(1)
    
    return photos_df

# Function to create list of unique cities
def create_unique_locations_list(photos_df):
    """Creates list of unique locations without duplicates"""
    # Create DataFrame with only location information (without file paths and coordinates)
    locations_df = photos_df[['city', 'state', 'country']].copy()
    
    # Remove rows where city is not defined
    locations_df = locations_df.dropna(subset=['city'])
    
    # Remove duplicates
    unique_locations_df = locations_df.drop_duplicates()
    
    # Sort by country and city
    unique_locations_df = unique_locations_df.sort_values(by=['country', 'state', 'city'])
    
    return unique_locations_df

# Main program function
def main():
    # Load cache from file at program start
    global location_cache
    location_cache = load_cache_from_file()
    print(f"Loaded {len(location_cache)} entries from cache.")
    
    # Path to directory with photos (can be changed as needed)
    photos_directory = "c:/temp/"
    
    # Check directory existence
    if not os.path.exists(photos_directory):
        print(f"Directory {photos_directory} does not exist!")
        return
    
    print(f"Scanning directory {photos_directory}...")
    
    # Scan directory and get data
    photos_df = scan_photos_directory(photos_directory)
    
    # Display scanning results
    print(f"Found {len(photos_df)} photos.")
    print(f"Of these, {photos_df['latitude'].notna().sum()} have GPS coordinates.")
    
    # If there are photos with coordinates, determine location
    if photos_df['latitude'].notna().sum() > 0:
        print("\nDetermining location by GPS coordinates...")
        photos_df = add_location_info(photos_df)
        
        # Display statistics by cities
        cities = photos_df['city'].dropna().value_counts()
        print("\nCities found:")
        for city, count in cities.items():
            print(f"{city}: {count} photos")
        
        # Create list of unique locations
        unique_locations = create_unique_locations_list(photos_df)
        
        # Save list of unique locations to CSV file
        unique_locations_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'unique_locations.csv')
        unique_locations.to_csv(unique_locations_file, index=False, encoding='utf-8')
        print(f"\nList of unique locations saved to file: {unique_locations_file}")
        
        # Display list of unique locations
        print("\nList of unique locations:")
        for _, row in unique_locations.iterrows():
            location_str = f"{row['city']}"
            if row['state']:
                location_str += f", {row['state']}"
            if row['country']:
                location_str += f", {row['country']}"
            print(location_str)
        
        # Display cache statistics
        print(f"\nCaching statistics:")
        print(f"Total unique coordinates in cache: {len(location_cache)}")
    
    # Save results to CSV file
    output_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'photos_gps_data.csv')
    photos_df.to_csv(output_file, index=False, encoding='utf-8')
    print(f"\nData saved to file: {output_file}")
    
    # Display first few rows of the table
    print("\nData example:")
    print(photos_df.head())
    
    # Save cache to file when program ends
    save_cache_to_file(location_cache)

if __name__ == "__main__":
    main()