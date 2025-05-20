#!/usr/bin/env python
"""
Script to check prediction API functionality
"""
import requests
import json
import time

# Wait for server to start
print("Waiting for server to start...")
time.sleep(3)

# Try to access the predictions API endpoint
try:
    # First try to login to get a token
    login_data = {'username': 'admin', 'password': 'adminpassword'}
    try:
        login_response = requests.post('http://127.0.0.1:8000/api/auth/login/', data=login_data)
        
        if login_response.status_code == 200:
            token = login_response.json().get('token', '')
            headers = {'Authorization': f'Token {token}'}
            print("Successfully logged in and got auth token")
        else:
            print(f"Login failed with status code: {login_response.status_code}")
            print(login_response.text)
            headers = {}
    except Exception as e:
        print(f"Login error: {str(e)}")
        headers = {}

    # Now make the API request (with token if available)
    response = requests.get('http://127.0.0.1:8000/api/analytics/predictions/', headers=headers)
    
    if response.status_code == 200:
        print("API request successful!")
        
        # Parse and display predictions
        data = response.json()
        
        # Check if we have prediction data in the expected format
        if 'low_review_score_db' in data and 'high_review_score_db' in data:
            # Check for and print feature_importance and top_5_products to verify format
            
            # Sample sales trend prediction
            if data['low_review_score_db']['future_sales_trend']:
                sample = data['low_review_score_db']['future_sales_trend'][0]
                print("\nSample Future Sales Trend Prediction:")
                print(f"Period: {sample['prediction_period']}")
                print(f"Value: {sample['predicted_value']}")
                
                # Check if details contains formatted feature_importance
                if 'details' in sample and sample['details']:
                    if isinstance(sample['details'], dict) and 'feature_importance' in sample['details']:
                        print("\nFeature Importance:")
                        print(json.dumps(sample['details']['feature_importance'], indent=2))
            
            # Sample top product prediction
            if data['low_review_score_db']['future_top_product']:
                sample = data['low_review_score_db']['future_top_product'][0]
                print("\nSample Future Top Product Prediction:")
                print(f"Period: {sample['prediction_period']}")
                print(f"Value: {sample['predicted_value']}")
                
                # Check if details contains top products
                if 'details' in sample and sample['details']:
                    if isinstance(sample['details'], dict):
                        # Check for both old and new keys
                        if 'top_5_products' in sample['details']:
                            print("\nUsing old key 'top_5_products':")
                            print(sample['details']['top_5_products'])
                        
                        if 'Top 5 Products' in sample['details']:
                            print("\nUsing new key 'Top 5 Products':")
                            print(sample['details']['Top 5 Products'])
                            
                        if 'predicted_sales_values' in sample['details']:
                            print("\nUsing old key 'predicted_sales_values':")
                            print(json.dumps(sample['details']['predicted_sales_values'], indent=2))
                        
                        if 'Product Sales Values' in sample['details']:
                            print("\nUsing new key 'Product Sales Values':")
                            print(json.dumps(sample['details']['Product Sales Values'], indent=2))
        else:
            print("Unexpected API response format:")
            print(json.dumps(data, indent=2))
    else:
        print(f"API request failed with status code: {response.status_code}")
        print(response.text)
except Exception as e:
    print(f"Error accessing API: {str(e)}")
