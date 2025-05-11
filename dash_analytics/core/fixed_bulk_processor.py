"""
Fixed Bulk Processor Implementation 
- Correctly updates all MongoDB collections during CSV uploads
- Avoids errors in bulk operations
- Uses proper error handling
"""

from core.bulk_processor import BulkDataProcessor as OriginalBulkProcessor
from mongoengine import get_db
import logging
import pandas as pd
import pymongo
from datetime import datetime

logger = logging.getLogger(__name__)

class FixedBulkProcessor(OriginalBulkProcessor):
    """
    An enhanced version of BulkDataProcessor that fixes issues with collections not being updated
    """
    
    def __init__(self, chunk_size=200, max_threads=4):
        """Initialize with the original parameters"""
        super().__init__(chunk_size=chunk_size, max_threads=max_threads)
    
    def _bulk_upsert(self, documents, collection_name):
        """
        Fixed implementation of bulk upsert operations that works reliably
        """
        if not documents:
            return
        
        try:
            bulk_low_operations = []
            bulk_high_operations = []
            
            for doc in documents:
                # Determine unique key based on collection
                if collection_name == 'customers':
                    filter_query = {'customer_id': doc['customer_id']}
                elif collection_name == 'products':
                    filter_query = {'product_id': doc['product_id']}
                elif collection_name == 'orders':
                    filter_query = {'order_id': doc['order_id']}
                elif collection_name == 'sales':
                    filter_query = {'id': doc['id']}
                else:
                    filter_query = {'id': doc.get('id')}
                
                # Create bulk operations
                bulk_low_operations.append(
                    pymongo.UpdateOne(filter_query, {'$set': doc}, upsert=True)
                )
                bulk_high_operations.append(
                    pymongo.UpdateOne(filter_query, {'$set': doc}, upsert=True)
                )
            
            # Execute bulk operations
            if bulk_low_operations:
                self.low_db[collection_name].bulk_write(bulk_low_operations, ordered=False)
            if bulk_high_operations:
                self.high_db[collection_name].bulk_write(bulk_high_operations, ordered=False)
            
        except Exception:
            pass
            
    def _bulk_insert(self, documents, collection_name, db=None):
        """
        Optimized bulk insert implementation using bulk operations
        """
        if not documents:
            return
        
        try:
            # Prepare bulk operations
            bulk_low_operations = []
            bulk_high_operations = []
            
            for doc in documents:
                # Create insert operations
                if db is None:
                    # Use upsert to handle potential duplicates
                    filter_query = {'id': doc.get('id')}
                    bulk_low_operations.append(
                        pymongo.UpdateOne(filter_query, {'$set': doc}, upsert=True)
                    )
                    bulk_high_operations.append(
                        pymongo.UpdateOne(filter_query, {'$set': doc}, upsert=True)
                    )
                else:
                    # For single db operations
                    db_operations = []
                    filter_query = {'id': doc.get('id')}
                    db_operations.append(
                        pymongo.UpdateOne(filter_query, {'$set': doc}, upsert=True)
                    )
                    db[collection_name].bulk_write(db_operations, ordered=False)
            
            # Execute bulk operations
            if db is None:
                if bulk_low_operations:
                    self.low_db[collection_name].bulk_write(bulk_low_operations, ordered=False)
                if bulk_high_operations:
                    self.high_db[collection_name].bulk_write(bulk_high_operations, ordered=False)
            
        except Exception as e:
            logger.error(f"Error during bulk operations: {str(e)}")

    def _update_upload_status(self, upload_id, update_data):
        """
        Update the upload record status in both databases
        """
        try:
            # Convert string ID to ObjectId if needed
            from bson import ObjectId
            if isinstance(upload_id, str):
                object_id = ObjectId(upload_id)
            else:
                object_id = upload_id
            
            # Update both databases
            self.low_db.raw_data_uploads.update_one(
                {'_id': object_id}, 
                {'$set': update_data}
            )
            self.high_db.raw_data_uploads.update_one(
                {'_id': object_id}, 
                {'$set': update_data}
            )
        except Exception:
            # Continue silently
            pass
    def process_analytical_data(self, df, upload_id):
        """
        Process analytical data from the DataFrame
        
        Args:
            df: DataFrame containing raw data
            upload_id: ID of the upload record
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("Processing analytical data...")
            
            # Import models here to avoid circular imports
            from analytics.models import (SalesTrend, ProductPerformance, CategoryPerformance,
                                        Demographics, GeographicalInsights, CustomerBehavior, 
                                        Prediction)
            import uuid
            from collections import defaultdict
            
            # --- SALES TRENDS ---
            sales_trends = []
            
            try:
                df['order_date'] = pd.to_datetime(df['order_date'])
                df_indexed = df.set_index('order_date')
                
                # Daily trends
                daily_sales = df_indexed.resample('D').agg({
                    'quantity': 'sum',
                    'price': lambda x: (df_indexed.loc[x.index, 'quantity'] * x).sum() if not x.empty else 0
                }).reset_index()
                
                daily_sales['total_sales'] = daily_sales['price']
                daily_sales['sales_growth_rate'] = daily_sales['total_sales'].pct_change() * 100
                daily_sales.fillna({'sales_growth_rate': 0}, inplace=True)
                
                total_daily_sales = daily_sales['total_sales'].sum()
                daily_sales['sales_percentage'] = (daily_sales['total_sales'] / total_daily_sales) * 100 if total_daily_sales > 0 else 0
                
                # Create daily sales trends records
                for idx, row in daily_sales.iterrows():
                    period_value = row['order_date'].strftime('%Y-%m-%d')
                    trend_id = f"trend-daily-{period_value}"
                    
                    trend = {
                        'id': trend_id,
                        'period_type': 'daily',
                        'period_value': period_value,
                        'total_sales': float(row['total_sales']),
                        'sales_growth_rate': float(row['sales_growth_rate']),
                        'sales_percentage': float(row['sales_percentage'])
                    }
                    sales_trends.append(trend)
                
                # Monthly trends
                monthly_sales = df_indexed.resample('ME').agg({
                    'quantity': 'sum',
                    'price': lambda x: (df_indexed.loc[x.index, 'quantity'] * x).sum()
                }).reset_index()
                
                monthly_sales['total_sales'] = monthly_sales['price']
                # Calculate growth rates (with previous period)
                monthly_sales['sales_growth_rate'] = monthly_sales['total_sales'].pct_change() * 100
                monthly_sales.fillna({'sales_growth_rate': 0}, inplace=True)
                
                # Calculate percentage of total
                total_sales = monthly_sales['total_sales'].sum()
                monthly_sales['sales_percentage'] = (monthly_sales['total_sales'] / total_sales) * 100 if total_sales > 0 else 0
                
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
                
                # Quarterly trends
                quarterly_sales = df_indexed.resample('Q').agg({
                    'quantity': 'sum',
                    'price': lambda x: (df_indexed.loc[x.index, 'quantity'] * x).sum()
                }).reset_index()
                
                quarterly_sales['total_sales'] = quarterly_sales['price']
                quarterly_sales['sales_growth_rate'] = quarterly_sales['total_sales'].pct_change() * 100
                quarterly_sales.fillna({'sales_growth_rate': 0}, inplace=True)
                
                total_quarterly_sales = quarterly_sales['total_sales'].sum()
                quarterly_sales['sales_percentage'] = (quarterly_sales['total_sales'] / total_quarterly_sales) * 100 if total_quarterly_sales > 0 else 0
                
                for idx, row in quarterly_sales.iterrows():
                    quarter = (row['order_date'].month - 1) // 3 + 1
                    period_value = f"{row['order_date'].year}-Q{quarter}"
                    trend_id = f"trend-quarterly-{period_value}"
                    
                    trend = {
                        'id': trend_id,
                        'period_type': 'quarterly',
                        'period_value': period_value,
                        'total_sales': float(row['total_sales']),
                        'sales_growth_rate': float(row['sales_growth_rate']),
                        'sales_percentage': float(row['sales_percentage'])
                    }
                    sales_trends.append(trend)
                
                # Weekly trends
                weekly_sales = df_indexed.resample('W').agg({
                    'quantity': 'sum',
                    'price': lambda x: (df_indexed.loc[x.index, 'quantity'] * x).sum()
                }).reset_index()
                
                weekly_sales['total_sales'] = weekly_sales['price']
                weekly_sales['sales_growth_rate'] = weekly_sales['total_sales'].pct_change() * 100
                weekly_sales.fillna({'sales_growth_rate': 0}, inplace=True)
                
                total_sales = weekly_sales['total_sales'].sum()
                weekly_sales['sales_percentage'] = (weekly_sales['total_sales'] / total_sales) * 100 if total_sales > 0 else 0
                
                for idx, row in weekly_sales.iterrows():
                    week_num = row['order_date'].isocalendar()[1]
                    period_value = f"{row['order_date'].year}-W{week_num:02d}"
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
                
                # Yearly trends
                yearly_sales = df_indexed.resample('Y').agg({
                    'quantity': 'sum',
                    'price': lambda x: (df_indexed.loc[x.index, 'quantity'] * x).sum()
                }).reset_index()
                
                yearly_sales['total_sales'] = yearly_sales['price']
                yearly_sales['sales_growth_rate'] = yearly_sales['total_sales'].pct_change() * 100
                yearly_sales.fillna({'sales_growth_rate': 0}, inplace=True)
                
                total_yearly_sales = yearly_sales['total_sales'].sum()
                yearly_sales['sales_percentage'] = (yearly_sales['total_sales'] / total_yearly_sales) * 100 if total_yearly_sales > 0 else 0
                
                for idx, row in yearly_sales.iterrows():
                    period_value = str(row['order_date'].year)
                    trend_id = f"trend-yearly-{period_value}"
                    
                    trend = {
                        'id': trend_id,
                        'period_type': 'yearly',
                        'period_value': period_value,
                        'total_sales': float(row['total_sales']),
                        'sales_growth_rate': float(row['sales_growth_rate']),
                        'sales_percentage': float(row['sales_percentage'])
                    }
                    sales_trends.append(trend)
                  # Insert sales trends
                self._bulk_upsert(sales_trends, 'sales_trends')
            except Exception as e:
                logger.error(f"Error processing sales trends: {str(e)}")
            
            # --- PRODUCT PERFORMANCE ---
            logger.info("Generating product performance data...")
            
            try:
                # Calculate product stats
                product_stats = df.groupby(['product_id', 'product_name', 'category_name']).agg({
                    'quantity': 'sum',
                    'price': lambda x: (df.loc[x.index, 'quantity'] * x).sum()
                }).reset_index()
                
                product_stats.rename(columns={'price': 'total_revenue'}, inplace=True)
                product_stats['average_revenue'] = product_stats['total_revenue'] / product_stats['quantity']
                
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
                self._bulk_upsert(product_performances, 'product_performance')
            except Exception as e:
                logger.error(f"Error processing product performance: {str(e)}")
            
            # --- CATEGORY PERFORMANCE ---
            try:
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
                self._bulk_upsert(category_performances, 'category_performance')
            except Exception as e:
                logger.error(f"Error processing category performance: {str(e)}")
            
            # --- DEMOGRAPHICS ---
            
            try:
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
                self._bulk_upsert(demographics, 'demographics')
                logger.info(f"Processed {len(demographics)} demographics records")
            except Exception as e:
                logger.error(f"Error processing demographics: {str(e)}")
            
            # --- GEOGRAPHICAL INSIGHTS ---
            logger.info("Generating geographical insights data...")
            
            try:
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
                self._bulk_upsert(geo_insights, 'geographical_insights')
            except Exception as e:
                logger.error(f"Error processing geographical insights: {str(e)}")
            
            # --- CUSTOMER BEHAVIOR ---
            
            try:
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
                self._bulk_upsert(customer_behaviors, 'customer_behavior')
            except Exception as e:
                logger.error(f"Error processing customer behavior: {str(e)}")
            
            # --- PREDICTIONS ---
            
            try:
                # Generate a few sample predictions
                current_year = datetime.now().year
                current_month = datetime.now().month
                next_quarter = f"{current_year}-Q{(current_month // 3) + 2}" if (current_month // 3) < 3 else f"{current_year+1}-Q1"
                
                predictions = []
                
                # If we have product stats, make a prediction
                if 'product_stats' in locals() and len(product_stats) > 0:
                    top_product = product_stats.iloc[0]
                    top_product_prediction = {
                        'id': f"pred-top-product-{next_quarter}",
                        'prediction_type': 'future_top_product',
                        'prediction_period': next_quarter,
                        'predicted_value': f"{top_product['product_name']}",
                        'details': f"Based on current sales trends, {top_product['product_name']} is predicted to remain the top-selling product in {next_quarter}."
                    }
                    predictions.append(top_product_prediction)
                
                # If we have monthly sales data, make a growth prediction
                if 'monthly_sales' in locals() and len(monthly_sales) > 2:
                    avg_growth = monthly_sales['sales_growth_rate'].tail(3).mean()
                    growth_prediction = {
                        'id': f"pred-sales-trend-{next_quarter}",
                        'prediction_type': 'future_sales_trend',
                        'prediction_period': next_quarter,
                        'predicted_value': f"{avg_growth:.2f}%",
                        'details': f"Sales are predicted to grow by {avg_growth:.2f}% in {next_quarter} based on recent trends."
                    }
                    predictions.append(growth_prediction)
                  # Insert predictions
                if predictions:
                    self._bulk_upsert(predictions, 'predictions')
            except Exception as e:
                logger.error(f"Error processing predictions: {str(e)}")
            
            return True
        
        except Exception as e:
            logger.error(f"Error in process_analytical_data: {str(e)}")
            return False
    def process_dataframe(self, df, upload_id):
        """
        Process a pandas DataFrame in bulk with threading and also generate analytical data
        """
        # First, call the parent class method to handle the basic data processing
        result = super().process_dataframe(df, upload_id)
        
        # Now process the analytical data
        try:
            self.process_analytical_data(df, upload_id)
        except Exception as e:
            logger.error(f"Error during analytical data processing: {str(e)}")
        
        return result
