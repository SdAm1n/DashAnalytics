#!/usr/bin/env python3
import requests
import json
from datetime import datetime, timedelta

# Test configuration
BASE_URL = "http://localhost:8001/api"
# For a real app, we would authenticate properly, but for testing we'll just use the session cookie
# This is just a test script to see if the API is working correctly

def test_sales_trend_api():
    """Test the sales trend API endpoint"""
    print("Testing Sales Trend API...")
    
    # Set up dates
    today = datetime.now()
    six_months_ago = today - timedelta(days=180)
    
    # Format dates
    date_from = six_months_ago.strftime('%Y-%m-%d')
    date_to = today.strftime('%Y-%m-%d')
    
    # Try different periods
    periods = ['daily', 'weekly', 'monthly', 'quarterly', 'yearly']
    
    for period in periods:
        url = f"{BASE_URL}/analytics/sales_trend/?period={period}&date_from={date_from}&date_to={date_to}"
        print(f"\nTesting period: {period}")
        print(f"URL: {url}")
        
        try:
            # Make the request
            response = requests.get(url)
            
            # Check if the request was successful
            if response.status_code == 200:
                print(f"Success! Response status: {response.status_code}")
                data = response.json()
                print(f"Received {len(data)} data points")
                if data and len(data) > 0:
                    print("First data point:")
                    print(json.dumps(data[0], indent=2))
            else:
                print(f"Error! Response status: {response.status_code}")
                print(response.text)
                
        except Exception as e:
            print(f"Exception occurred: {e}")
    
    print("\nTesting category filter...")
    url = f"{BASE_URL}/analytics/sales_trend/?period=monthly&category=Electronics&date_from={date_from}&date_to={date_to}"
    print(f"URL: {url}")
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            print(f"Success with category filter! Response status: {response.status_code}")
            data = response.json()
            print(f"Received {len(data)} data points")
        else:
            print(f"Error with category filter! Response status: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"Exception occurred: {e}")

if __name__ == "__main__":
    test_sales_trend_api()
