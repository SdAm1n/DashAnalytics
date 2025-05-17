#!/usr/bin/env python
"""
Test script for Customer Behavior API and Loyalty Segments

This script tests the Customer Behavior API and verifies that the
loyalty segments are being properly returned.
"""
import requests
import json
import sys
import time


def test_customer_behavior_api():
    """Test the customer behavior API and loyalty segments"""
    print("Testing Customer Behavior API...")

    try:
        # Get data from the API
        response = requests.get(
            "http://127.0.0.1:8000/api/analytics/customer_behavior/")

        if response.status_code != 200:
            print(f"ERROR: API returned status code {response.status_code}")
            print(response.text)
            return False

        # Parse the response
        data = response.json()

        # Verify that the loyalty segments are present
        if 'customer_loyalty' not in data:
            print("ERROR: 'customer_loyalty' is missing from the API response")
            return False

        if 'loyalty_segments' not in data['customer_loyalty']:
            print("ERROR: 'loyalty_segments' is missing from the customer_loyalty data")
            return False

        loyalty_segments = data['customer_loyalty']['loyalty_segments']

        # Check that all expected loyalty segments are present
        expected_segments = ['new', 'occasional', 'regular', 'loyal']
        for segment in expected_segments:
            if segment not in loyalty_segments:
                print(
                    f"ERROR: '{segment}' segment is missing from loyalty_segments")
                return False

            if not isinstance(loyalty_segments[segment], (int, float)):
                print(
                    f"ERROR: '{segment}' segment value is not a number: {loyalty_segments[segment]}")
                return False

        # Check if any segment has data (not all zeros)
        has_data = any(loyalty_segments[segment]
                       > 0 for segment in loyalty_segments)
        if not has_data:
            print("WARNING: All loyalty segments have zero values")

        # Print the loyalty segments data
        print("Loyalty segments data:")
        print(json.dumps(loyalty_segments, indent=2))

        print("Customer Behavior API test passed!")
        return True

    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to the server. Is the Django server running?")
        return False
    except Exception as e:
        print(f"ERROR: An unexpected error occurred: {str(e)}")
        return False


if __name__ == "__main__":
    # Wait a moment for the server to start if it was just launched
    print("Waiting for server to be ready...")
    time.sleep(2)

    # Run the test
    success = test_customer_behavior_api()

    # Exit with appropriate code
    sys.exit(0 if success else 1)
