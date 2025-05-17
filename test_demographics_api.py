#!/usr/bin/env python
import os
import sys
import json
import requests
from datetime import datetime

# Add Django project path to system path
sys.path.insert(0, '/home/s010p/SWE_DB_Project/DashAnalytics')


# Test the Demographics API

def test_demographics_api():
    print("Testing Demographics API...")

    # Define the base URL
    base_url = "http://localhost:8000"

    # Test different time periods
    periods = ['7d', '30d', '90d', '1y', 'all']

    for period in periods:
        print(f"\nTesting period: {period}")
        response = requests.get(
            f'{base_url}/api/analytics/demographics/?period={period}')

        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()

            # Print key metrics
            print("\nKey Metrics:")
            print(f"Average Age: {data.get('average_age')}")
            print(f"Gender Ratio: {data.get('gender_ratio')}")
            print(
                f"Most Active Age Group: {data.get('most_active_age_group')}")

            # Print age distribution summary
            print("\nAge Distribution:")
            age_dist = data.get('age_distribution', {})
            if age_dist:
                for label, count in zip(age_dist.get('labels', []), age_dist.get('values', [])):
                    print(f"{label}: {count}")

            # Print gender distribution
            gender_dist = data.get('gender_distribution', {})
            print(
                f"\nGender Distribution: Male: {gender_dist.get('male', 0)}, Female: {gender_dist.get('female', 0)}")

            # Print sample of detailed demographics
            print("\nSample of Detailed Demographics:")
            details = data.get('detailed_demographics', [])
            for i, group in enumerate(details[:3]):  # Print first 3
                print(
                    f"  {group.get('age_group')}: {group.get('total_customers')} customers, ${group.get('total_sales'):.2f} sales")

            # Print gender_age_sales data (the fixed chart data)
            print("\nGender Age Sales Chart Data:")
            gender_age_sales = data.get('gender_age_sales', {})
            if gender_age_sales:
                age_groups = gender_age_sales.get('age_groups', [])
                male_sales = gender_age_sales.get('male_sales', [])
                female_sales = gender_age_sales.get('female_sales', [])

                print(f"Age Groups: {age_groups}")
                print(f"Male Sales: {male_sales}")
                print(f"Female Sales: {female_sales}")

                # Check if data is valid (non-zero)
                has_data = any(male_sales) or any(female_sales)
                print(f"Chart has valid data: {has_data}")
        else:
            print(f"Error: {response.content.decode()}")


if __name__ == "__main__":
    test_demographics_api()
