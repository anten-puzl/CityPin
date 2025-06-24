# CityPin

CityPin is a tool for analyzing geolocation data from photos and determining the cities where they were taken.

## Description

The program recursively scans a specified folder containing photos, extracts GPS coordinates from EXIF metadata, and determines city, region, and country names using the Nominatim API (OpenStreetMap). Results are saved to CSV files for further analysis.

## Features

- Recursive scanning of a folder with photos
- Supported formats: `.jpg`, `.jpeg`, `.tiff`, `.png`
- Extraction of GPS coordinates from EXIF metadata
- City, region, and country lookup via Nominatim API
- Caching of API results (with ~1 km coordinate granularity)
- Persistent cache between runs (`location_cache.json`)
- Generation of a unique locations list
- Output to CSV files:
  - `photos_gps_data.csv` — full list of photos with coordinates and resolved locations
  - `unique_locations.csv` — unique found cities/regions/countries

## Requirements

- Python 3.6+
- Libraries:
  - pandas
  - pillow (PIL)
  - requests

## Installation

git clone https://github.com/yourusername/CityPin.git
cd CityPin
pip install pandas pillow requests

text

## Usage

1. In `photo_scanner.py`, set the `photos_directory` variable to the path of your photo folder:

photos_directory = "path/to/your/photos/"

text
2. Run the program:

python photo_scanner.py

text
3. After execution, the following files will appear in the program's folder:
- `photos_gps_data.csv` — table of all processed photos with coordinates and resolved locations
- `unique_locations.csv` — unique found cities/regions/countries
- `location_cache.json` — cache of Nominatim API queries

## Notes

- The program does not accept command-line arguments; all settings are specified in the code.
- GPS data must be present in the EXIF metadata of your photos for correct operation.
- To avoid exceeding Nominatim API limits, the program waits 1 second between API requests if the result is not found in the cache.
- On repeated runs, the cache is used to speed up processing and reduce API load.

## Output File Structure

**photos_gps_data.csv**:
| file_path           | latitude   | longitude  | city    | state     | country   | display_name             |
|---------------------|------------|------------|---------|-----------|-----------|--------------------------|
| path/to/photo1.jpg  | 40.712776  | -74.005974 | New York| New York  | United States | ...                  |

**unique_locations.csv**:
| city     | state     | country        |
|----------|-----------|----------------|
| New York | New York  | United States  |

---

If you need additional parameters or support for other formats, modify the code as needed.
