#!/usr/bin/env python
"""
Script to check prediction data directly from the Django shell.
"""
from analytics.models import Prediction
import os
import sys
import json
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dash_analytics.settings')
django.setup()


# Check each database
for db_alias in ['high_review_score_db', 'low_review_score_db']:
    print(f"\n{db_alias} Predictions:")

    # Get future sales trend predictions
    future_sales = list(Prediction.objects(prediction_type='future_sales_trend')
                        .using(db_alias).order_by('-prediction_period'))

    print(f"- Future Sales Trend Predictions: {len(future_sales)}")
    for pred in future_sales:
        print(f"  - {pred.prediction_period}: {pred.predicted_value}")
        try:
            details = json.loads(pred.details)
            print(f"    - Model: {details.get('model', 'Unknown')}")
            print(f"    - Confidence: {details.get('confidence', 'Unknown')}")
            # Print feature importance to check the format
            if 'feature_importance' in details:
                print(
                    f"    - Feature Importance: {json.dumps(details['feature_importance'], indent=2)}")
        except (json.JSONDecodeError, AttributeError) as e:
            print(f"    - Raw details: {pred.details}")

    # Get future top product predictions
    top_products = list(Prediction.objects(prediction_type='future_top_product')
                        .using(db_alias).order_by('-prediction_period'))

    print(f"- Future Top Product Predictions: {len(top_products)}")
    for pred in top_products:
        print(f"  - {pred.prediction_period}: {pred.predicted_value}")
        try:
            details = json.loads(pred.details)
            print(f"    - Model: {details.get('model', 'Unknown')}")
            # Check for renamed keys
            for key in details:
                if key.startswith('Top'):
                    print(f"    - {key}: {details[key][:3]}...")
                if key.startswith('Product'):
                    print(
                        f"    - {key}: {json.dumps(dict(list(details[key].items())[:2]))}...")
                if key == 'top_5_products':  # Check if the old key still exists
                    print(
                        f"    - Old Key Found: top_5_products: {details['top_5_products'][:3]}...")
        except (json.JSONDecodeError, AttributeError) as e:
            print(f"    - Raw details: {pred.details}")
