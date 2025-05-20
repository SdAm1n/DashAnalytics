#!/usr/bin/env python
"""
Test script to verify Random Forest predictions are working correctly.
This script checks if predictions exist in the database and displays them.
"""
from analytics.models import Prediction
import os
import sys
import json
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dash_analytics.settings')
django.setup()


def main():
    """Test the Random Forest predictions"""
    print("Testing Random Forest predictions...")

    # Check each database
    for db_alias in ['high_review_score_db', 'low_review_score_db']:
        print(f"\nChecking {db_alias}...")

        # Get future sales trend predictions
        future_sales = Prediction.objects(
            prediction_type='future_sales_trend'
        ).using(db_alias).order_by('-prediction_period')

        print(f"Found {len(future_sales)} future sales trend predictions")

        # Get future top product predictions
        top_products = Prediction.objects(
            prediction_type='future_top_product'
        ).using(db_alias).order_by('-prediction_period')

        print(f"Found {len(top_products)} future top product predictions")

        # Display sample predictions
        if future_sales:
            sample = future_sales[0]
            print(f"\nSample future sales trend prediction:")
            print(f"Period: {sample.prediction_period}")
            print(f"Value: {sample.predicted_value}")

            try:
                details = json.loads(sample.details)
                print(f"Model: {details.get('model', 'Unknown')}")
                print(f"Confidence: {details.get('confidence', 'Unknown')}")
            except (json.JSONDecodeError, AttributeError):
                print(f"Details: {sample.details}")

        if top_products:
            sample = top_products[0]
            print(f"\nSample future top product prediction:")
            print(f"Period: {sample.prediction_period}")
            print(f"Value: {sample.predicted_value}")

            try:
                details = json.loads(sample.details)
                print(f"Model: {details.get('model', 'Unknown')}")
                print(
                    f"Top products: {', '.join(details.get('top_5_products', ['Unknown'])[:3])}")
            except (json.JSONDecodeError, AttributeError):
                print(f"Details: {sample.details}")


if __name__ == "__main__":
    main()
