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
import datetime
import geocoder
import requests
import re

# Function definitions
def main():
 
    # global formatted_date  # Use global to modify the outer variable, not just local to fn
    if len(sys.argv) > 1:
        arg = sys.argv[1]
    else:
        arg = None

    # Transform the date input
    # If no argument is provided, the function will return today's date
    # If the argument is invalid, it will raise a ValueError
    formatted_date = transform_date(arg)

    # Get latitude and longitude
    latitude, longitude = get_location()
   
    if latitude is None or longitude is None:
        print("Could not retrieve location.")
        sys.exit(1)
    
    # Get the UTC offset
    utc_offset = get_utc_offset()

    # Now get sunrise and sunset info from the API
    # API URL
    url = "https://api.sunrisesunset.io/json"

    # Specify parameters
    params = {
        "lat": latitude,
        "lng": longitude,
        "timezone": utc_offset
    }

    # Only add the date parameter if it's not None
    if formatted_date:
        params["date"] = formatted_date

    # Sending the request
    response = requests.get(url, params=params)

    # Parse the JSON response
    data = response.json()

    # Extract and display specific data (which will be displayed as output of Alfred workflow if called from Alfred)
    print("On", data["results"]["date"])
    print("First light at", data["results"]["first_light"])
    print("Dawn at", data["results"]["dawn"])
    print("Sunrise at", data["results"]["sunrise"])
    print("Sunset at", data["results"]["sunset"])
    print("Last light at", data["results"]["last_light"])

def get_location():
    # Get the current location
    location = geocoder.ip('me')

    # Extract latitude and longitude
    latitude = location.latlng[0]
    longitude = location.latlng[1]

    return latitude, longitude

def get_utc_offset():
    # API to get location and timezone
    url = "http://worldtimeapi.org/api/ip"

    # Send the request
    response = requests.get(url)

    # Parse the JSON response
    data = response.json()

    # Extract UTC offset
    utc_offset = data["utc_offset"]

    return utc_offset

# Function to transform date input
def transform_date(arg):
    """
    Transforms a date string into a standard format (YYYY-MM-DD).
    Handles relative dates like t+5 or t-3 and absolute dates in various formats.
    Raises ValueError if the date cannot be parsed.
    """

    import warnings

    # Get the current date and year
    today = datetime.date.today()
    current_year = datetime.date.today().year

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
            #return today + datetime.timedelta(days=days_delta)
            result = today + datetime.timedelta(days=days_delta)
        else:
            result = today
        return result.strftime("%Y-%m-%d")
    # Attempt to parse the date in various formats; if no year then assume current year
    for fmt in ("%m/%d", "%m-%d", "%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y"):
        try:
            # Suppress warnings about leap years
            with warnings.catch_warnings(): 
                warnings.simplefilter("ignore", DeprecationWarning)
                dt = datetime.datetime.strptime(arg, fmt)

            if fmt in ("%m/%d", "%m-%d"):
                dt = dt.replace(year=today.year)
            return dt.date().strftime("%Y-%m-%d")
        except ValueError:
            continue

    # Could not parse
    #return "Invalid date"
    raise ValueError(f"Could not parse date: {arg}") 
        
if __name__ == "__main__":
    main()
    # Check if the script is being run directly
    # If so, call the main function
    # This is the entry point of the script
    # This allows the script to be run as a standalone program