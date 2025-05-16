#!/usr/bin/env python3
import requests
import json
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import argparse
from datetime import datetime, timedelta

"""
Test script for the Customer Behavior API
"""

def test_customer_behavior_api(base_url="http://localhost:8002/api", segment=None, limit=20, verbose=True):
    """Test the customer behavior API endpoint"""
    print("Testing Customer Behavior API...")
    
    # Construct URL with parameters
    url = f"{base_url}/analytics/customer_behavior/"
    params = {}
    
    if segment:
        params['segment'] = segment
    
    if limit:
        params['limit'] = limit
    
    if verbose:
        print(f"Request URL: {url}")
        if params:
            print(f"Parameters: {params}")
    
    try:
        # Make the request
        response = requests.get(url, params=params)
        
        # Check if the request was successful
        if response.status_code == 200:
            print(f"✓ Success! Response status: {response.status_code}")
            data = response.json()
            
            # Validate response structure
            validate_response_structure(data)
            
            # Optional: show detailed data
            if verbose:
                print("\nResponse Data Structure:")
                for key, value in data.items():
                    print(f"- {key}: {type(value).__name__}")
                    if isinstance(value, list) and len(value) > 0:
                        print(f"  - Contains {len(value)} items")
                        if len(value) > 0:
                            print(f"  - Sample item: {json.dumps(value[0])[:100]}...")
                    elif isinstance(value, dict):
                        print(f"  - Keys: {', '.join(value.keys())}")
                
            # Analyze the results
            analyze_results(data)
                
            return data
            
        else:
            print(f"✗ Error! Response status: {response.status_code}")
            try:
                print(response.json())
            except:
                print(response.text)
            return None
                
    except Exception as e:
        print(f"✗ Exception occurred: {e}")
        return None

def validate_response_structure(data):
    """Validate the structure of the API response"""
    # Check required sections
    required_sections = [
        'purchase_frequency', 
        'customer_loyalty', 
        'customer_segments', 
        'purchase_times',
        'top_customers'
    ]
    
    missing_sections = [section for section in required_sections if section not in data]
    
    if missing_sections:
        print(f"✗ Response validation failed: Missing required sections: {', '.join(missing_sections)}")
        return False
    
    # Check top customers structure
    if not data['top_customers'] or not isinstance(data['top_customers'], list):
        print("⚠ Warning: No top customers data or incorrect format")
    
    print("✓ Response structure validation passed")
    return True

def analyze_results(data):
    """Analyze and print insights from the API results"""
    # 1. Purchase Frequency
    if 'purchase_frequency' in data and 'average_purchases' in data['purchase_frequency']:
        avg_purchases = data['purchase_frequency']['average_purchases']
        median_purchases = data['purchase_frequency'].get('median_purchases', 'N/A')
        print(f"\nPurchase Frequency:")
        print(f"- Average purchases per customer: {avg_purchases:.1f}")
        print(f"- Median purchases per customer: {median_purchases}")
    
    # 2. Customer Loyalty
    if 'customer_loyalty' in data and 'loyalty_segments' in data['customer_loyalty']:
        segments = data['customer_loyalty']['loyalty_segments']
        total = sum(segments.values())
        print(f"\nCustomer Loyalty:")
        for segment, count in segments.items():
            percentage = (count / total * 100) if total > 0 else 0
            print(f"- {segment.title()}: {count} customers ({percentage:.1f}%)")
    
    # 3. Customer Segments
    if 'customer_segments' in data and 'segment_distribution' in data['customer_segments']:
        segments = data['customer_segments']['segment_distribution']
        print(f"\nCustomer Segments:")
        for segment in segments:
            print(f"- {segment['segment']}: {segment['count']} customers")
    
    # 4. Purchase Times
    if 'purchase_times' in data and 'weekly' in data['purchase_times']:
        weekly = data['purchase_times']['weekly']
        max_day = max(weekly, key=lambda x: x['purchases'])
        print(f"\nPurchase Times:")
        print(f"- Most popular day: {max_day['day']} ({max_day['purchases']} purchases)")
        
    # 5. Top Customers
    if 'top_customers' in data and len(data['top_customers']) > 0:
        total_spent = sum(customer['total_spent'] for customer in data['top_customers'])
        avg_spent = total_spent / len(data['top_customers']) if len(data['top_customers']) > 0 else 0
        print(f"\nTop Customers:")
        print(f"- Number of top customers: {len(data['top_customers'])}")
        print(f"- Average spent per top customer: ${avg_spent:.2f}")
        print(f"- Top customer: {data['top_customers'][0]['id']} (${data['top_customers'][0]['total_spent']:.2f})")

def visualize_data(data):
    """Create visualizations of the customer behavior data"""
    if not data:
        print("Cannot visualize: No data available")
        return
        
    # Visualize purchase frequency
    if 'purchase_frequency' in data and 'frequency_distribution' in data['purchase_frequency']:
        try:
            freq_data = data['purchase_frequency']['frequency_distribution']
            if freq_data:
                df = pd.DataFrame(freq_data)
                
                plt.figure(figsize=(10, 6))
                plt.bar(df['purchases'], df['customers'])
                plt.title('Purchase Frequency Distribution')
                plt.xlabel('Number of Purchases')
                plt.ylabel('Number of Customers')
                plt.grid(True, alpha=0.3)
                plt.tight_layout()
                plt.savefig('purchase_frequency.png')
                print("Purchase frequency chart saved as 'purchase_frequency.png'")
        except Exception as e:
            print(f"Error visualizing purchase frequency: {e}")
    
    # Visualize customer segments
    if 'customer_segments' in data and 'segment_distribution' in data['customer_segments']:
        try:
            segment_data = data['customer_segments']['segment_distribution']
            if segment_data:
                segments = [item['segment'] for item in segment_data]
                counts = [item['count'] for item in segment_data]
                
                plt.figure(figsize=(10, 6))
                plt.pie(counts, labels=segments, autopct='%1.1f%%', startangle=90)
                plt.axis('equal')
                plt.title('Customer Segments')
                plt.tight_layout()
                plt.savefig('customer_segments.png')
                print("Customer segments chart saved as 'customer_segments.png'")
        except Exception as e:
            print(f"Error visualizing customer segments: {e}")
    
    # Visualize purchase times
    if 'purchase_times' in data and 'weekly' in data['purchase_times']:
        try:
            weekly_data = data['purchase_times']['weekly']
            if weekly_data:
                days = [item['day'] for item in weekly_data]
                purchases = [item['purchases'] for item in weekly_data]
                
                plt.figure(figsize=(12, 6))
                plt.bar(days, purchases)
                plt.title('Purchases by Day of Week')
                plt.xlabel('Day of Week')
                plt.ylabel('Number of Purchases')
                plt.grid(True, alpha=0.3)
                plt.tight_layout()
                plt.savefig('purchase_times.png')
                print("Purchase times chart saved as 'purchase_times.png'")
        except Exception as e:
            print(f"Error visualizing purchase times: {e}")

def parse_arguments():
    parser = argparse.ArgumentParser(description='Test the Customer Behavior API')
    parser.add_argument('-u', '--url', default='http://localhost:8002/api',
                        help='Base API URL (default: http://localhost:8002/api)')
    parser.add_argument('-s', '--segment', 
                        choices=['VIP', 'Regular', 'Occasional', 'New', 'At Risk', 'all'],
                        help='Customer segment to filter by')
    parser.add_argument('-l', '--limit', type=int, default=20,
                        help='Number of top customers to return (default: 20)')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Enable verbose output')
    parser.add_argument('--visualize', action='store_true',
                        help='Generate visualizations of the data')
    
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_arguments()
    
    data = test_customer_behavior_api(args.url, args.segment, args.limit, args.verbose)
    
    if data and args.visualize:
        visualize_data(data)
