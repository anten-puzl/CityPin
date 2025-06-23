# CityPin

CityPin is a tool for analyzing geolocation data from photos and identifying the cities where they were taken.

## Description

This program scans a specified directory of photos, extracts GPS coordinates from EXIF data, and determines the names of cities, regions, and countries using the Nominatim API (OpenStreetMap). Results are saved to CSV files for further analysis.

## Features

- Recursive scanning of photo directories
- Extraction of GPS coordinates from photo EXIF data
- Location determination (city, region, country) based on GPS coordinates
- Caching of API query results for optimization and faster operation
- Saving cache to file for use between program runs
- Proximity-based coordinate caching (within ~1km)
- Creating a list of unique locations
- Saving results to CSV files

## Requirements

- Python 3.6+
- Libraries:
  - pandas
  - pillow (PIL)
  - requests

## Installation

```bash
git clone https://github.com/yourusername/CityPin.git
cd CityPin
pip install pandas pillow requests