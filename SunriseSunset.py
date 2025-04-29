"""
This script gets the sunrise and sunset times for the user's current location
using optional date input (MM/DD). 
Date can be entered as relative date using T for today and +n (or -n) for n day offset.
If no argument is provided, today's date is used.
"""
# Check Python version and path
#!/usr/bin/env python3

# Import libraries
import sys
import argparse
from datetime import date, timedelta, datetime
import geocoder
import logging
import traceback
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import re

# argument 1 is API key. It is required for TimeZoneDB API.
# argument 2 is date_arg, followed by date or relative date. It is optional; default is today's date.
# argument 3 is optional flag for for DD/MM date formatted dates.
# argument 4 is optional flag for logging.

# Function definitions
def main():

    parser = argparse.ArgumentParser(description="Get sunrise/sunset information.")
    parser.add_argument("api_key", help="Your TimezoneDB API key")
    # Maybe the default should be set to today instead of doing this in the function in the following line, but need to format properly
    parser.add_argument("--date_arg", nargs='?', default=None, help="Date to get information for (in MM-DD format (or DD-MM if that format selected) or relative date like t+5 or t-3)")
    parser.add_argument("--DDMMformat", action="store_true", help="Use DD-MM date format instead of MM-DD")
    parser.add_argument("--log", action="store_true", help="Enable logging")

    # Parse the arguments
    args = parser.parse_args()
    api_key = args.api_key
    date = args.date_arg
    use_DDMMformat = args.DDMMformat
    log_enabled = args.log
   
    # Check if the API key is provided; if not, exit with an error message
    if not api_key:
        print("API key is required.")
        sys.exit(1)
    
    # Set up logging if the --log flag is provided
    if log_enabled:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        logging.info("Logging enabled.")
    
    # Transform the date input;
    # If no argument is provided, the function will return today's date;
    # If the argument is invalid, it will raise a ValueError
    try:
        formatted_date = transform_date(date, use_DDMMformat)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    # Get latitude and longitude
    latitude, longitude = get_location(log_enabled)
   
    if latitude is None or longitude is None:
        print("Could not retrieve location.")
        sys.exit(1)
    
    # Pass latitude and longitude to get the UTC offset
    utc_offset = get_utc_offset(latitude, longitude, api_key, log_enabled)
    if utc_offset is None:
        print("Error: Could not retrieve UTC offset.")
        sys.exit(1)

    print_sunrise_sunset_data(latitude, longitude, formatted_date, utc_offset)

def print_sunrise_sunset_data(latitude, longitude, formatted_date, utc_offset):
    """Fetches and prints sunrise/sunset data."""

    url = "https://api.sunrisesunset.io/json"
    params = {"lat": latitude, "lng": longitude, "timezone": utc_offset}
    if formatted_date:
        params["date"] = formatted_date

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        date_object = datetime.strptime(data["results"]["date"], "%Y-%m-%d")
        verbose_date = date_object.strftime("%A, %B %d, %Y")

        print(f"On {verbose_date}:")
        print(f"First light at: {data['results']['first_light']}")
        print(f"Dawn at: {data['results']['dawn']}")
        print(f"Sunrise at: {data['results']['sunrise']}")
        print(f"Sunset at: {data['results']['sunset']}")
        print(f"Last light at: {data['results']['last_light']}")

    except requests.exceptions.RequestException as e:
        print(f"Error: Could not retrieve sunrise/sunset data: {e}")
        if log_enabled:
            logging.error(f"Request error: {e}")
            logging.error(traceback.format_exc())
        sys.exit(1)


def get_location(log_enabled): 
    """Gets the user's latitude and longitude."""
    try:
        location = geocoder.ip('me', timeout=5)  # Set a timeout for the geocoder request
        if location:
            if location.latlng:
                return location.latlng
            else:
                if log_enabled:
                    logging.error("Geocoder: Could not retrieve lat/lng from response.")
                return None, None
        else:
            if log_enabled:
                logging.error("Geocoder: Failed to get location.")
            return None, None
    except geocoder.exceptions.GeocoderTimedOut:
        if log_enabled:
            logging.error("Geocoder: Connection timed out.")
        return None, None
    except Exception as e:
        if log_enabled:
            logging.error(f"Geocoder: An unexpected error occurred: {e}")
            logging.error(traceback.format_exc())
        return None, None


def get_utc_offset(latitude, longitude, api_key, log_enabled):
    """
    Get the UTC offset for the given latitude and longitude using the TimeZoneDB API.
    This requires an API key.
    The function will retry the request up to 5 times in case of a failure.
    The function will log errors and return None if it fails to retrieve the UTC offset.
    Returns the UTC offset in hours.
    """
    # Set up logging
    if log_enabled:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # Check if latitude and longitude are valid
    if latitude is None or longitude is None:
        if log_enabled:
            logging.error("Invalid latitude or longitude.")
        return None
    
    # Timezone service URL
    url = "http://api.timezonedb.com/v2.1/get-time-zone"

    # API key (replace with your own)
    # api_key = "041RVIVT3U52"

    # Parameters for the API request
    params = {
        "key": api_key,
        "format": "json",
        "by": "position",
        "lat": latitude,  
        "lng": longitude, 
        "fields": "gmtOffset" # Only request the gmtOffset field
    }
    
    retry_strategy = Retry(
        total=5,  # Total number of retries
        backoff_factor=1,  # Wait 1s, 2s, 4s... between retries
        status_forcelist=[500, 502, 503, 504],  # HTTP status codes to retry on
        allowed_methods=["GET"]
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    http = requests.Session()
    http.mount("http://", adapter)
    http.mount("https://", adapter)

    try:
        response = http.get(url, params=params, timeout=5)  # Add a timeout
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        data = response.json()
        utc_offset = data["gmtOffset"]/3600  # Convert seconds to hours
        # Check if the response contains the expected data
        if "gmtOffset" not in data:
            if log_enabled:
                logging.error(f"Unexpected response format: {data}")
            return None
        # Check if the UTC offset is a valid number
        if not isinstance(utc_offset, (int, float)):
            if log_enabled:
                logging.error(f"Invalid UTC offset: {utc_offset}")
            return None
        # Check if the UTC offset is within a reasonable range
        if utc_offset < -12 or utc_offset > 14:
            if log_enabled:
                logging.error(f"UTC offset out of range: {utc_offset}")
            return None
        # Log the successful retrieval of UTC offset
        if log_enabled:
            logging.info(f"UTC offset retrieved successfully: {utc_offset} hours")
        # Return the UTC offset
        return utc_offset
    
    except requests.exceptions.RequestException as e:
        if log_enabled:
            logging.error(f"Error accessing {url} after retries: {e}")
            logging.error(traceback.format_exc())  # Log the full traceback
        return None
    

# Function to transform date input
def transform_date(arg, use_DDMMformat):
    """
    Transforms a date string into a standard format (YYYY-MM-DD).
    Handles relative dates like t+5 or t-3 and absolute dates in various formats.
    Raises ValueError if the date cannot be parsed.
    """

    import warnings

    # Get the current date and year
    today = date.today()


    if not arg:
        # If no argument, just use today's date
        return today.strftime("%Y-%m-%d")
    
    arg = ''.join(arg.lower().split()) # Remove spaces and convert to lowercase

    # Check if the argument is a relative date (e.g., t+5 or t-3) and handle them
    match = re.fullmatch(r't([+-]\d+)?', arg)
    if match:
        offset = match.group(1)
        if offset:
            days_delta = int(offset)
            #return today + timedelta(days=days_delta)
            result = today + timedelta(days=days_delta)
        else:
            result = today
        return result.strftime("%Y-%m-%d")
   
    # Attempt to parse the date in various formats; if no year then assume current year
    if use_DDMMformat:
        # If use_DDMMformat format is selected, try to parse it as DD-MM
        formats = ("%d/%m", "%d-%m", "%Y-%d-%m", "%d/%m/%Y", "%d-%m-%Y")
    else:
        # Otherwise, try to parse it as MM-DD
        formats = ("%m/%d", "%m-%d", "%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y")
    # Try to parse the date in various formats
    for fmt in formats:
        try:
            # Suppress warnings about leap years
            with warnings.catch_warnings(): 
                warnings.simplefilter("ignore", DeprecationWarning)
                dt = datetime.strptime(arg, fmt)

            if fmt in ("%d/%m", "%d-%m"):
                dt = dt.replace(year=today.year)
            return dt.date().strftime("%Y-%m-%d")
        except ValueError:
            continue

    # Could not parse
    #return "Invalid date"
    raise ValueError(f"Could not parse date: {arg}") 
        
if __name__ == "__main__":
    main()
# The script can be run from the command line with the following command:
# python SunriseSunset.py <API_KEY> [--date_arg <DATE>] [--DDMMformat] [--log]
# Example usage:
#   python SunriseSunset.py 041RVIVT3U52 --date_arg t+5 --DDMMformat --log
#   python SunriseSunset.py 041RVIVT3U52 --date_arg t+5 --log
