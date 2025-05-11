"""
CSV Data Upload Fix - A direct solution for the DashAnalytics CSV upload issue
"""
import os
import sys
import django
import pandas as pd
import logging
from datetime import datetime

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dash_analytics.settings')
django.setup()

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import the necessary components
from mongoengine import get_db
from core.models import RawDataUpload, Customer, Product, Order, Sales
from analytics.models import (SalesTrend, ProductPerformance, CategoryPerformance,
                             Demographics, GeographicalInsights, CustomerBehavior, Prediction)
from bson import ObjectId
import uuid
from collections import defaultdict

def fix_csv_upload():
    """
    Fix the CSV upload functionality by adding a direct implementation
    that correctly updates all MongoDB collections
    """
    try:
        print("\n=== Starting CSV Upload Fix ===\n")
        
        # Print initial state
        print("Initial database state:")
        print(f"Customers: {Customer.objects.count()}")
        print(f"Products: {Product.objects.count()}")
        print(f"Orders: {Order.objects.count()}")
        print(f"Sales: {Sales.objects.count()}")
        
        # Get database connections
        low_db = get_db('low_review_score_db')
        high_db = get_db('high_review_score_db')
        
        # Load test data
        file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_data.csv')
        print(f"\nLoading test data from {file_path}")
        
        df = pd.read_csv(file_path)
        print(f"Loaded {len(df)} rows")
        
        # Create upload record
        upload = RawDataUpload(file_name="csv_upload_fix_test.csv")
        upload.save()
        upload_id = upload.id
        print(f"Created upload record with ID: {upload_id}")
        
        # Extract data from DataFrame
        print("\nExtracting and processing data...")
        
        # Process customers
        customers = {}
        for _, row in df.iterrows():
            customer_id = int(row['customer_id'])
            if customer_id not in customers:
                customers[customer_id] = {
                    'customer_id': customer_id,
                    'gender': str(row['gender']),
                    'age': int(row['age']),
                    'city': str(row['city'])
                }
        
        # Process products
        products = {}
        for _, row in df.iterrows():
            product_id = int(row['product_id'])
            if product_id not in products:
                products[product_id] = {
                    'product_id': product_id,
                    'product_name': str(row['product_name']),
                    'category_id': int(row['category_id']),
                    'category_name': str(row['category_name']),
                    'price': float(row['price'])
                }
        
        # Process orders and sales
        orders = []
        sales = []
        low_reviews = []
        high_reviews = []
        
        for _, row in df.iterrows():
            # Create order ID
            order_date = pd.to_datetime(row['order_date'])
            order_id = f"ORD-{row['customer_id']}-{row['product_id']}-{order_date.strftime('%Y%m%d%H%M%S')}"
            
            # Order data
            order = {
                'order_id': order_id,
                'order_date': order_date,
                'customer_id': int(row['customer_id']),
                'product_id': int(row['product_id']),
                'quantity': int(row['quantity']),
                'payment_method': row.get('payment_method', 'Cash'),
                'review_score': float(row['review_score']) if pd.notna(row.get('review_score')) else None
            }
            orders.append(order)
            
            # Sales data
            sale = {
                'id': f"SALE-{order_id}",
                'customer_id': str(row['customer_id']),
                'product_id': str(row['product_id']),
                'quantity': int(row['quantity']),
                'sale_date': order_date,
                'revenue': float(row['quantity'] * row['price']),
                'profit': float(row['quantity'] * row['price'] * 0.3),
                'city': row['city']
            }
            sales.append(sale)
            
            # Review data if present
            if pd.notna(row.get('review_score')):
                review_score = float(row['review_score'])
                review_data = {
                    'id': f"REV-{order_id}",
                    'customer_id': str(row['customer_id']),
                    'product_id': str(row['product_id']),
                    'review_score': review_score,
                    'sentiment': 'Positive' if review_score >= 4 else 'Negative' if review_score <= 2 else 'Neutral',
                    'review_text': row.get('review_text', ''),
                    'review_date': order_date
                }
                
                if review_score < 4:
                    low_reviews.append(review_data)
                else:
                    high_reviews.append(review_data)
        
        # Insert data into MongoDB collections
        print("\nInserting data into MongoDB collections...")
        
        # Insert customers
        for customer in customers.values():
            # Insert into both databases using update
            low_db.customers.update_one(
                {'customer_id': customer['customer_id']},
                {'$set': customer},
                upsert=True
            )
            high_db.customers.update_one(
                {'customer_id': customer['customer_id']},
                {'$set': customer},
                upsert=True
            )
        print(f"Inserted {len(customers)} customers")
        
        # Insert products
        for product in products.values():
            # Insert into both databases using update
            low_db.products.update_one(
                {'product_id': product['product_id']},
                {'$set': product},
                upsert=True
            )
            high_db.products.update_one(
                {'product_id': product['product_id']},
                {'$set': product},
                upsert=True
            )
        print(f"Inserted {len(products)} products")
        
        # Insert orders
        for order in orders:
            # Insert into both databases using update
            low_db.orders.update_one(
                {'order_id': order['order_id']},
                {'$set': order},
                upsert=True
            )
            high_db.orders.update_one(
                {'order_id': order['order_id']},
                {'$set': order},
                upsert=True
            )
        print(f"Inserted {len(orders)} orders")
        
        # Insert sales
        for sale in sales:
            # Insert into both databases using update
            low_db.sales.update_one(
                {'id': sale['id']},
                {'$set': sale},
                upsert=True
            )
            high_db.sales.update_one(
                {'id': sale['id']},
                {'$set': sale},
                upsert=True
            )
        print(f"Inserted {len(sales)} sales")
        
        # Insert reviews
        for review in low_reviews:
            low_db.low_reviews.update_one(
                {'id': review['id']},
                {'$set': review},
                upsert=True
            )
        print(f"Inserted {len(low_reviews)} low reviews")
        
        for review in high_reviews:
            high_db.high_reviews.update_one(
                {'id': review['id']},
                {'$set': review},
                upsert=True
            )
        print(f"Inserted {len(high_reviews)} high reviews")
        
        # Generate and insert analytical data
        generate_analytical_data(df, low_db, high_db)
        
        # Update the upload record
        upload.status = 'completed'
        upload.processed_records = len(df)
        upload.total_records = len(df)
        upload.low_reviews_count = len(low_reviews)
        upload.high_reviews_count = len(high_reviews)
        upload.processing_time = 1.0  # Dummy value
        upload.save()
        print(f"Updated upload record: {upload.id}")
          # Generate and insert analytical data
        generate_analytical_data(df, low_db, high_db)
        
        # Print final state
        print("\nFinal database state:")
        print(f"Customers: {Customer.objects.count()}")
        print(f"Products: {Product.objects.count()}")
        print(f"Orders: {Order.objects.count()}")
        print(f"Sales: {Sales.objects.count()}")
        
        # Also check analytical collections
        print("\nAnalytical collections:")
        print(f"Sales Trends: {low_db.sales_trends.count_documents({})}")
        print(f"Product Performance: {low_db.product_performance.count_documents({})}")
        print(f"Category Performance: {low_db.category_performance.count_documents({})}")
        print(f"Demographics: {low_db.demographics.count_documents({})}")
        print(f"Geographical Insights: {low_db.geographical_insights.count_documents({})}")
        print(f"Customer Behavior: {low_db.customer_behavior.count_documents({})}")
        print(f"Predictions: {low_db.predictions.count_documents({})}")
        
        print("\n=== CSV Upload Fix Complete ===\n")
        return True
    
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def generate_analytical_data(df, low_db, high_db):
    """
    Generate analytical data from the CSV data and insert it into appropriate collections
    
    Args:
        df: The pandas DataFrame containing the raw data
        low_db: The low review score database connection
        high_db: The high review score database connection
    """
    print("\nGenerating analytical data...")
    
    # --- SALES TRENDS ---
    print("Generating sales trends data...")
    # Group by day, week, month, and year
    sales_trends = []
    
    # Create monthly trends
    monthly_sales = df.groupby(pd.Grouper(key='order_date', freq='M')).agg({
        'quantity': 'sum',
        'price': lambda x: (df['quantity'] * df['price']).sum()
    }).reset_index()
    
    monthly_sales['total_sales'] = monthly_sales['price']
    # Calculate growth rates (with previous period)
    monthly_sales['sales_growth_rate'] = monthly_sales['total_sales'].pct_change() * 100
    monthly_sales.fillna({'sales_growth_rate': 0}, inplace=True)
    
    # Calculate percentage of total
    total_sales = monthly_sales['total_sales'].sum()
    monthly_sales['sales_percentage'] = (monthly_sales['total_sales'] / total_sales) * 100
    
    # Create sales trends records
    for idx, row in monthly_sales.iterrows():
        period_value = row['order_date'].strftime('%Y-%m')
        trend_id = f"trend-monthly-{period_value}"
        
        trend = {
            'id': trend_id,
            'period_type': 'monthly',
            'period_value': period_value,
            'total_sales': float(row['total_sales']),
            'sales_growth_rate': float(row['sales_growth_rate']),
            'sales_percentage': float(row['sales_percentage'])
        }
        sales_trends.append(trend)
    
    # Create weekly trends
    weekly_sales = df.groupby(pd.Grouper(key='order_date', freq='W')).agg({
        'quantity': 'sum',
        'price': lambda x: (df['quantity'] * df['price']).sum()
    }).reset_index()
    
    weekly_sales['total_sales'] = weekly_sales['price']
    weekly_sales['sales_growth_rate'] = weekly_sales['total_sales'].pct_change() * 100
    weekly_sales.fillna({'sales_growth_rate': 0}, inplace=True)
    
    total_sales = weekly_sales['total_sales'].sum()
    weekly_sales['sales_percentage'] = (weekly_sales['total_sales'] / total_sales) * 100
    
    for idx, row in weekly_sales.iterrows():
        period_value = f"{row['order_date'].year}-W{row['order_date'].week:02d}"
        trend_id = f"trend-weekly-{period_value}"
        
        trend = {
            'id': trend_id,
            'period_type': 'weekly',
            'period_value': period_value,
            'total_sales': float(row['total_sales']),
            'sales_growth_rate': float(row['sales_growth_rate']),
            'sales_percentage': float(row['sales_percentage'])
        }
        sales_trends.append(trend)
    
    # Insert sales trends
    print(f"Inserting {len(sales_trends)} sales trend records...")
    for trend in sales_trends:
        low_db.sales_trends.update_one(
            {'id': trend['id']},
            {'$set': trend},
            upsert=True
        )
        high_db.sales_trends.update_one(
            {'id': trend['id']},
            {'$set': trend},
            upsert=True
        )
    
    # --- PRODUCT PERFORMANCE ---
    print("Generating product performance data...")
    
    # Calculate product stats
    product_stats = df.groupby(['product_id', 'product_name', 'category_name']).agg({
        'quantity': 'sum',
        'price': lambda x: (df.loc[x.index, 'quantity'] * x).sum()
    }).reset_index()
    
    product_stats.rename(columns={'price': 'total_revenue'}, inplace=True)
    product_stats['average_revenue'] = product_stats['total_revenue'] / product_stats['quantity']
    
    # Flag best/worst selling products
    product_stats = product_stats.sort_values('quantity', ascending=False)
    
    product_performances = []
    
    # Determine best and worst selling products
    if len(product_stats) > 0:
        best_selling_idx = product_stats['quantity'].idxmax()
        worst_selling_idx = product_stats['quantity'].idxmin()
        
        # Find the category with highest profit
        category_profits = df.groupby('category_name').apply(
            lambda x: (x['quantity'] * x['price'] * 0.3).sum()
        ).reset_index(name='total_profit')
        
        highest_profit_category = ''
        if len(category_profits) > 0:
            highest_profit_category = category_profits.loc[category_profits['total_profit'].idxmax(), 'category_name']
    
    # Create performance records
    for idx, row in product_stats.iterrows():
        is_best = (idx == best_selling_idx) if 'best_selling_idx' in locals() else False
        is_worst = (idx == worst_selling_idx) if 'worst_selling_idx' in locals() else False
        is_highest_profit = (row['category_name'] == highest_profit_category) if 'highest_profit_category' in locals() else False
        
        perf = {
            'id': f"perf-{row['product_id']}",
            'product_id': str(row['product_id']),
            'category': row['category_name'],
            'total_quantity_sold': int(row['quantity']),
            'average_revenue': float(row['average_revenue']),
            'is_best_selling': is_best,
            'is_worst_selling': is_worst,
            'is_highest_profit_category': is_highest_profit
        }
        product_performances.append(perf)
    
    # Insert product performances
    print(f"Inserting {len(product_performances)} product performance records...")
    for perf in product_performances:
        low_db.product_performance.update_one(
            {'id': perf['id']},
            {'$set': perf},
            upsert=True
        )
        high_db.product_performance.update_one(
            {'id': perf['id']},
            {'$set': perf},
            upsert=True
        )
    
    # --- CATEGORY PERFORMANCE ---
    print("Generating category performance data...")
    
    # Calculate category stats
    category_stats = df.groupby('category_name').agg({
        'quantity': 'sum',
        'price': lambda x: (df.loc[x.index, 'quantity'] * x).sum()
    }).reset_index()
    
    category_stats.rename(columns={'price': 'total_revenue'}, inplace=True)
    category_stats['average_revenue'] = category_stats['total_revenue'] / category_stats['quantity']
    
    # Calculate profit per category
    category_stats['total_profit'] = category_stats['total_revenue'] * 0.3  # Assuming 30% profit margin
    
    # Determine highest profit category
    if len(category_stats) > 0:
        highest_profit_idx = category_stats['total_profit'].idxmax()
    
    category_performances = []
    
    for idx, row in category_stats.iterrows():
        is_highest_profit = (idx == highest_profit_idx) if 'highest_profit_idx' in locals() else False
        
        cat_perf = {
            'id': f"cat-{row['category_name'].replace(' ', '-').lower()}",
            'category': row['category_name'],
            'total_quantity_sold': int(row['quantity']),
            'average_revenue': float(row['average_revenue']),
            'highest_profit': is_highest_profit
        }
        category_performances.append(cat_perf)
    
    # Insert category performances
    print(f"Inserting {len(category_performances)} category performance records...")
    for perf in category_performances:
        low_db.category_performance.update_one(
            {'id': perf['id']},
            {'$set': perf},
            upsert=True
        )
        high_db.category_performance.update_one(
            {'id': perf['id']},
            {'$set': perf},
            upsert=True
        )
    
    # --- DEMOGRAPHICS ---
    print("Generating demographics data...")
    
    # Create age groups
    def get_age_group(age):
        if age < 18:
            return "Under 18"
        elif age < 30:
            return "18-29"
        elif age < 45:
            return "30-44"
        elif age < 65:
            return "45-64"
        else:
            return "65+"
    
    # Add age group column
    df['age_group'] = df['age'].apply(get_age_group)
    
    # Group by age group and gender
    demographics_data = df.groupby(['age_group', 'gender']).agg({
        'customer_id': 'nunique',  # count unique customers
        'price': lambda x: (df.loc[x.index, 'quantity'] * x).sum()
    }).reset_index()
    
    demographics_data.rename(columns={'customer_id': 'total_customers', 'price': 'total_spent'}, inplace=True)
    
    demographics = []
    
    for idx, row in demographics_data.iterrows():
        demo_id = f"demo-{row['age_group'].replace(' ', '-').lower()}-{row['gender'].lower()}"
        
        demo = {
            'id': demo_id,
            'age_group': row['age_group'],
            'gender': row['gender'],
            'total_customers': int(row['total_customers']),
            'total_spent': float(row['total_spent'])
        }
        demographics.append(demo)
    
    # Insert demographics data
    print(f"Inserting {len(demographics)} demographics records...")
    for demo in demographics:
        low_db.demographics.update_one(
            {'id': demo['id']},
            {'$set': demo},
            upsert=True
        )
        high_db.demographics.update_one(
            {'id': demo['id']},
            {'$set': demo},
            upsert=True
        )
    
    # --- GEOGRAPHICAL INSIGHTS ---
    print("Generating geographical insights data...")
    
    # Group by city
    geo_data = df.groupby('city').agg({
        'order_date': 'count',  # Count orders
        'price': lambda x: (df.loc[x.index, 'quantity'] * x).sum()
    }).reset_index()
    
    geo_data.rename(columns={'order_date': 'total_orders', 'price': 'total_sales'}, inplace=True)
    geo_data['average_order_value'] = geo_data['total_sales'] / geo_data['total_orders']
    
    geo_insights = []
    
    for idx, row in geo_data.iterrows():
        geo_id = f"geo-{row['city'].replace(' ', '-').lower()}"
        
        insight = {
            'id': geo_id,
            'city': row['city'],
            'total_sales': float(row['total_sales']),
            'total_orders': int(row['total_orders']),
            'average_order_value': float(row['average_order_value'])
        }
        geo_insights.append(insight)
    
    # Insert geographical insights
    print(f"Inserting {len(geo_insights)} geographical insight records...")
    for insight in geo_insights:
        low_db.geographical_insights.update_one(
            {'id': insight['id']},
            {'$set': insight},
            upsert=True
        )
        high_db.geographical_insights.update_one(
            {'id': insight['id']},
            {'$set': insight},
            upsert=True
        )
    
    # --- CUSTOMER BEHAVIOR ---
    print("Generating customer behavior data...")
    
    # Group by customer
    customer_data = df.groupby('customer_id').agg({
        'order_date': 'count',  # Count purchases
        'price': lambda x: (df.loc[x.index, 'quantity'] * x).sum()
    }).reset_index()
    
    customer_data.rename(columns={'order_date': 'total_purchases', 'price': 'total_spent'}, inplace=True)
    
    # Calculate purchase frequency (purchases per month)
    min_date = df['order_date'].min()
    max_date = df['order_date'].max()
    
    # Calculate number of months in the data
    months_diff = (max_date.year - min_date.year) * 12 + (max_date.month - min_date.month)
    months_diff = max(1, months_diff)  # Ensure at least 1 month
    
    customer_data['purchase_frequency'] = customer_data['total_purchases'] / months_diff
    
    # Define customer segments
    def get_customer_segment(row):
        if row['total_spent'] > 1000 or row['purchase_frequency'] >= 2:
            return "VIP"
        elif row['total_spent'] > 500 or row['purchase_frequency'] >= 1:
            return "Regular"
        else:
            return "Occasional"
    
    customer_data['customer_segment'] = customer_data.apply(get_customer_segment, axis=1)
    
    customer_behaviors = []
    
    for idx, row in customer_data.iterrows():
        behavior_id = f"behavior-{row['customer_id']}"
        
        behavior = {
            'id': behavior_id,
            'customer_id': str(row['customer_id']),
            'total_purchases': int(row['total_purchases']),
            'total_spent': float(row['total_spent']),
            'purchase_frequency': float(row['purchase_frequency']),
            'customer_segment': row['customer_segment']
        }
        customer_behaviors.append(behavior)
    
    # Insert customer behaviors
    print(f"Inserting {len(customer_behaviors)} customer behavior records...")
    for behavior in customer_behaviors:
        low_db.customer_behavior.update_one(
            {'id': behavior['id']},
            {'$set': behavior},
            upsert=True
        )
        high_db.customer_behavior.update_one(
            {'id': behavior['id']},
            {'$set': behavior},
            upsert=True
        )
    
    # --- PREDICTIONS ---
    print("Generating prediction data...")
    
    # Generate a few sample predictions
    current_year = datetime.now().year
    current_month = datetime.now().month
    next_quarter = f"{current_year}-Q{(current_month // 3) + 2}" if (current_month // 3) < 3 else f"{current_year+1}-Q1"
    
    # Top product prediction
    if len(product_stats) > 0:
        top_product = product_stats.iloc[0]
        top_product_prediction = {
            'id': f"pred-top-product-{next_quarter}",
            'prediction_type': 'future_top_product',
            'prediction_period': next_quarter,
            'predicted_value': f"{top_product['product_name']}",
            'details': f"Based on current sales trends, {top_product['product_name']} is predicted to remain the top-selling product in {next_quarter}."
        }
        
        # Sales growth prediction
        avg_growth = monthly_sales['sales_growth_rate'].tail(3).mean()
        growth_prediction = {
            'id': f"pred-sales-trend-{next_quarter}",
            'prediction_type': 'future_sales_trend',
            'prediction_period': next_quarter,
            'predicted_value': f"{avg_growth:.2f}%",
            'details': f"Sales are predicted to grow by {avg_growth:.2f}% in {next_quarter} based on recent trends."
        }
        
        predictions = [top_product_prediction, growth_prediction]
        
        # Insert predictions
        print(f"Inserting {len(predictions)} prediction records...")
        for prediction in predictions:
            low_db.predictions.update_one(
                {'id': prediction['id']},
                {'$set': prediction},
                upsert=True
            )
            high_db.predictions.update_one(
                {'id': prediction['id']},
                {'$set': prediction},
                upsert=True
            )
    
    print("All analytical data generated and inserted successfully!")

if __name__ == "__main__":
    fix_csv_upload()
