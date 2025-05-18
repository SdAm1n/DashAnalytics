#!/usr/bin/env python
"""
Script to directly check prediction data in the database
"""
import os
import sys
import json
import django
import time

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dash_analytics.settings')
django.setup()

from analytics.models import Prediction

print("Using direct database access to check predictions...")

# Check each database
for db_alias in ['high_review_score_db', 'low_review_score_db']:
    print(f"\n{db_alias} Predictions:")
    
    # Get future sales trend predictions
    future_sales = list(Prediction.objects(prediction_type='future_sales_trend')
                      .using(db_alias).order_by('-prediction_period'))
    
    if future_sales:
        sample = future_sales[0]
        print("\nSample Future Sales Trend Prediction:")
        print(f"Period: {sample.prediction_period}")
        print(f"Value: {sample.predicted_value}")
        
        # Check details format
        try:
            details = json.loads(sample.details)
            print("Details format:")
            print(json.dumps(details, indent=2))
            
            if 'feature_importance' in details:
                print("\nFeature Importance:")
                print(json.dumps(details['feature_importance'], indent=2))
        except Exception as e:
            print(f"Error parsing details: {e}")
    
    # Get future top product predictions
    top_products = list(Prediction.objects(prediction_type='future_top_product')
                      .using(db_alias).order_by('-prediction_period'))
    
    if top_products:
        sample = top_products[0]
        print("\nSample Future Top Product Prediction:")
        print(f"Period: {sample.prediction_period}")
        print(f"Value: {sample.predicted_value}")
        
        # Check details format
        try:
            details = json.loads(sample.details)
            print("Details format:")
            print(json.dumps(details, indent=2))
            
            # Check for our new keys
            if 'Top 5 Products' in details:
                print("\nFound new key 'Top 5 Products'")
            else:
                print("\nOld key 'top_5_products' still being used")
                
            if 'Product Sales Values' in details:
                print("\nFound new key 'Product Sales Values'")
            else:
                print("\nOld key 'predicted_sales_values' still being used")
        except Exception as e:
            print(f"Error parsing details: {e}")
