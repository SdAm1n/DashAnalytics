#!/usr/bin/env python3
import requests
import json
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import pandas as pd
import argparse

"""
Advanced test script for the Sales Trend API
This script tests all features of the Sales Trend API and provides visual feedback
"""

def test_sales_trend_api(base_url="http://localhost:8001/api", period="monthly", category="all", verbose=True):
    """Test the sales trend API endpoint with various parameters"""
    print(f"Testing Sales Trend API with period={period}, category={category}...")
    
    # Set up dates
    today = datetime.now()
    one_year_ago = today - timedelta(days=365)
    
    # Format dates
    date_from = one_year_ago.strftime('%Y-%m-%d')
    date_to = today.strftime('%Y-%m-%d')
    
    # Construct URL with parameters
    url = f"{base_url}/analytics/sales_trend/?period={period}&category={category}&date_from={date_from}&date_to={date_to}"
    
    if verbose:
        print(f"Request URL: {url}")
    
    try:
        # Make the request
        response = requests.get(url)
        
        # Check if the request was successful
        if response.status_code == 200:
            print(f"✓ Success! Response status: {response.status_code}")
            data = response.json()
            
            if not data:
                print("✗ Error: Received empty data array")
                return None
                
            print(f"✓ Received {len(data)} data points")
            
            # Validate response structure
            validate_response_structure(data)
            
            # Optional: show detailed data
            if verbose and data and len(data) > 0:
                print("\nSample data point:")
                print(json.dumps(data[0], indent=2))
                
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
    if not data or len(data) == 0:
        print("✗ Response validation failed: Empty data")
        return False
        
    first_item = data[0]
    
    # Check required fields
    required_fields = ['period', 'total_sales', 'order_count', 'growth_rate']
    for field in required_fields:
        if field not in first_item:
            print(f"✗ Response validation failed: Missing required field '{field}'")
            return False
    
    # Check if first record has category and region data
    if 'category_sales' not in first_item:
        print("⚠ Warning: No category sales data in response")
    
    if 'region_sales' not in first_item:
        print("⚠ Warning: No region sales data in response")
    
    print("✓ Response structure validation passed")
    return True

def visualize_data(data, period):
    """Create a simple visualization of the data"""
    if not data or len(data) == 0:
        print("Cannot visualize: No data available")
        return
        
    # Convert to DataFrame for easier plotting
    df = pd.DataFrame(data)
    
    # Create figure with subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
    
    # Plot total sales
    ax1.plot(df['period'], df['total_sales'], marker='o', linestyle='-', linewidth=2, markersize=6)
    ax1.set_title(f'Sales Trend ({period})', fontsize=16)
    ax1.set_ylabel('Total Sales ($)', fontsize=12)
    ax1.grid(True, alpha=0.3)
    
    # Plot growth rate
    ax2.plot(df['period'], df['growth_rate'], marker='s', linestyle='-', linewidth=2, markersize=6, color='green')
    ax2.set_title(f'Growth Rate ({period})', fontsize=16)
    ax2.set_ylabel('Growth Rate (%)', fontsize=12)
    ax2.set_xlabel('Period', fontsize=12)
    ax2.grid(True, alpha=0.3)
    
    # Add value labels
    for x, y in zip(df['period'], df['total_sales']):
        ax1.annotate(f"{y:.0f}", (x, y), textcoords="offset points", xytext=(0,5), ha='center')
    
    for x, y in zip(df['period'], df['growth_rate']):
        ax2.annotate(f"{y:.1f}%", (x, y), textcoords="offset points", xytext=(0,5), ha='center')
    
    # Rotate x-axis labels if needed
    plt.xticks(rotation=45)
    
    plt.tight_layout()
    plt.savefig(f'sales_trend_{period}.png')
    print(f"Visualization saved as 'sales_trend_{period}.png'")
    
    # Try to display the plot
    try:
        plt.show()
    except:
        print("Could not display the plot interactively. Image has been saved.")

def test_all_periods_and_categories(base_url="http://localhost:8001/api"):
    """Run tests for all period types and some categories"""
    periods = ['daily', 'weekly', 'monthly', 'quarterly', 'yearly']
    
    # First test with default category (all)
    results = {}
    for period in periods:
        print(f"\n{'='*80}\nTesting period: {period}")
        data = test_sales_trend_api(base_url, period)
        results[period] = data
        
    # Then test a specific category
    print(f"\n{'='*80}\nTesting with category filter")
    data = test_sales_trend_api(base_url, "monthly", "Electronics")
    
    # Visualize the monthly data
    if 'monthly' in results and results['monthly']:
        visualize_data(results['monthly'], 'monthly')
        
    return results

def parse_arguments():
    parser = argparse.ArgumentParser(description='Test the Sales Trend API')
    parser.add_argument('-u', '--url', default='http://localhost:8001/api',
                        help='Base API URL (default: http://localhost:8001/api)')
    parser.add_argument('-p', '--period', default='monthly', 
                        choices=['daily', 'weekly', 'monthly', 'quarterly', 'yearly'],
                        help='Time period for aggregation (default: monthly)')
    parser.add_argument('-c', '--category', default='all',
                        help='Product category to filter by (default: all)')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Enable verbose output')
    parser.add_argument('-a', '--all', action='store_true',
                        help='Test all periods and some categories')
    
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_arguments()
    
    if args.all:
        test_all_periods_and_categories(args.url)
    else:
        data = test_sales_trend_api(args.url, args.period, args.category, args.verbose)
        if data:
            visualize_data(data, args.period)
