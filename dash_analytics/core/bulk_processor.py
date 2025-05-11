"""
Bulk Data Processing Module for DashAnalytics

Provides high-performance data processing functionality for CSV uploads:
1. Bulk inserts instead of individual .save() operations
2. Threading for parallel data processing
3. Chunk processing for large files
4. Optimized database connections
"""

import logging
import pandas as pd
import threading
import queue
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from mongoengine import get_db
from pymongo import UpdateOne, InsertOne
from pymongo.errors import BulkWriteError
from django.conf import settings
from bson import ObjectId

logger = logging.getLogger(__name__)

class BulkDataProcessor:
    """
    Handles bulk data processing and insertion for CSV uploads
    """
    def __init__(self, chunk_size=1000, max_threads=4):
        """
        Initialize the processor
        
        Args:
            chunk_size: Number of records to process in a single batch
            max_threads: Maximum number of worker threads for parallel processing
        """
        self.chunk_size = chunk_size
        self.max_threads = max_threads
        self.results_queue = queue.Queue()
        self.low_db = get_db('low_review_score_db')
        self.high_db = get_db('high_review_score_db')
    
    def process_dataframe(self, df, upload_id):
        """
        Process a pandas DataFrame in bulk with threading
        
        Args:
            df: Pandas DataFrame containing the data
            upload_id: ID of the upload record
            
        Returns:
            dict: Processing statistics and status
        """
        total_records = len(df)
        stats = {
            'total_records': total_records,
            'processed_records': 0,
            'failed_records': 0,
            'high_reviews_count': 0,
            'low_reviews_count': 0,
            'processing_time': 0
        }
        
        start_time = datetime.now()
        
        # Update upload record with total records
        self._update_upload_status(upload_id, {'total_records': total_records})
        
        # Split dataframe into chunks
        chunk_dfs = [df[i:i+self.chunk_size] for i in range(0, len(df), self.chunk_size)]
        logger.info(f"Processing {len(chunk_dfs)} chunks of size {self.chunk_size}")
        
        # Process chunks with thread pool
        with ThreadPoolExecutor(max_workers=self.max_threads) as executor:
            # Submit all chunks for processing
            futures = [executor.submit(self._process_chunk, chunk_df, i, upload_id) 
                      for i, chunk_df in enumerate(chunk_dfs)]
            
            # Collect results as they complete
            for future in futures:
                chunk_result = future.result()
                stats['processed_records'] += chunk_result['processed']
                stats['failed_records'] += chunk_result['failed']
                stats['high_reviews_count'] += chunk_result['high_reviews']
                stats['low_reviews_count'] += chunk_result['low_reviews']
                
                # Update progress in upload record every chunk
                progress = {
                    'processed_records': stats['processed_records'],
                    'high_reviews_count': stats['high_reviews_count'],
                    'low_reviews_count': stats['low_reviews_count']
                }
                self._update_upload_status(upload_id, progress)
        
        # Process all analytics data together to ensure complete analytical collections
        logger.info("Processing full analytics data for all chunks...")
        try:
            # Create a copy of the original dataframe to process complete analytical data
            # This ensures the analytical collections have complete data
            full_analytics_df = df.copy()
            process_analytics_in_background(full_analytics_df)
            logger.info("Successfully processed complete analytical data")
        except Exception as e:
            logger.error(f"Error processing complete analytical data: {str(e)}")
        
        # Mark upload as completed
        end_time = datetime.now()
        stats['processing_time'] = (end_time - start_time).total_seconds()
        self._update_upload_status(
            upload_id, 
            {'status': 'completed', 'processing_time': stats['processing_time']}
        )
        
        logger.info(f"Completed processing {stats['processed_records']} records in {stats['processing_time']:.2f} seconds")
        return stats
        
    def _process_chunk(self, chunk_df, chunk_index, upload_id):
        """
        Process a single chunk of data
        
        Args:
            chunk_df: DataFrame chunk to process
            chunk_index: Index of the chunk
            upload_id: Upload record ID
            
        Returns:
            dict: Chunk processing statistics
        """
        logger.info(f"Processing chunk {chunk_index} with {len(chunk_df)} records")
        result = {
            'processed': 0,
            'failed': 0,
            'high_reviews': 0,
            'low_reviews': 0
        }
        
        try:
            # Extract data for each collection
            customers_data = self._extract_customers(chunk_df)
            products_data = self._extract_products(chunk_df)
            orders_data = self._extract_orders(chunk_df)
            sales_data = self._extract_sales(chunk_df)
            low_reviews_data, high_reviews_data = self._extract_reviews(chunk_df)
            
            # Perform bulk inserts for each collection
            self._bulk_upsert(customers_data, 'customers')
            self._bulk_upsert(products_data, 'products')
            self._bulk_upsert(orders_data, 'orders')
            self._bulk_upsert(sales_data, 'sales')
            
            # Handle reviews with sharding
            if low_reviews_data:
                self._bulk_insert(low_reviews_data, 'low_reviews', db=self.low_db)
                result['low_reviews'] = len(low_reviews_data)
                
            if high_reviews_data:
                self._bulk_insert(high_reviews_data, 'high_reviews', db=self.high_db)
                result['high_reviews'] = len(high_reviews_data)
            
            # Process analytical data for this chunk
            if chunk_index == 0:  # Only process analytics for the first chunk to avoid duplication
                # Create a copy of the dataframe to avoid modifying the original
                analytics_df = chunk_df.copy()
                process_analytics_in_background(analytics_df)
                logger.info(f"Processed analytical data for chunk {chunk_index}")
            
            result['processed'] = len(chunk_df)
            
        except Exception as e:
            logger.error(f"Error processing chunk {chunk_index}: {str(e)}")
            result['failed'] = len(chunk_df)
            
        return result
    
    def _extract_customers(self, chunk_df):
        """Extract and transform customer data from DataFrame"""
        customers = {}
        for _, row in chunk_df.iterrows():
            customer_id = int(row['customer_id'])
            customers[customer_id] = {
                'customer_id': customer_id,
                'gender': str(row['gender']),
                'age': int(row['age']),
                'city': str(row['city'])
            }
        return list(customers.values())
    
    def _extract_products(self, chunk_df):
        """Extract and transform product data from DataFrame"""
        products = {}
        for _, row in chunk_df.iterrows():
            product_id = int(row['product_id'])
            products[product_id] = {
                'product_id': product_id,
                'product_name': str(row['product_name']),
                'category_id': int(row['category_id']),
                'category_name': str(row['category_name']),
                'price': float(row['price'])
            }
        return list(products.values())
    
    def _extract_orders(self, chunk_df):
        """Extract and transform order data from DataFrame"""
        orders = []
        for _, row in chunk_df.iterrows():
            order_date = pd.to_datetime(row['order_date'])
            order_id = f"ORD-{row['customer_id']}-{row['product_id']}-{order_date.strftime('%Y%m%d%H%M%S')}"
            
            orders.append({
                'order_id': order_id,
                'order_date': order_date,
                'customer_id': int(row['customer_id']),
                'product_id': int(row['product_id']),
                'quantity': int(row['quantity']),
                'payment_method': row.get('payment_method', 'Cash'),
                'review_score': float(row['review_score']) if pd.notna(row.get('review_score')) else None
            })
        return orders
    
    def _extract_sales(self, chunk_df):
        """Extract and transform sales data from DataFrame"""
        sales = []
        for _, row in chunk_df.iterrows():
            order_date = pd.to_datetime(row['order_date'])
            order_id = f"ORD-{row['customer_id']}-{row['product_id']}-{order_date.strftime('%Y%m%d%H%M%S')}"
            
            sales.append({
                'id': f"SALE-{order_id}",
                'customer_id': str(row['customer_id']),
                'product_id': str(row['product_id']),
                'quantity': int(row['quantity']),
                'sale_date': order_date,
                'revenue': float(row['quantity'] * row['price']),
                'profit': float(row['quantity'] * row['price'] * 0.3),
                'city': row['city']
            })
        return sales
    
    def _extract_reviews(self, chunk_df):
        """Extract and separate reviews by score"""
        low_reviews = []
        high_reviews = []
        
        for _, row in chunk_df.iterrows():
            if pd.notna(row.get('review_score')):
                order_date = pd.to_datetime(row['order_date'])
                order_id = f"ORD-{row['customer_id']}-{row['product_id']}-{order_date.strftime('%Y%m%d%H%M%S')}"
                
                review_data = {
                    'id': f"REV-{order_id}",
                    'customer_id': str(row['customer_id']),
                    'product_id': str(row['product_id']),
                    'review_score': float(row['review_score']),
                    'sentiment': self._get_sentiment(float(row['review_score'])),
                    'review_text': row.get('review_text', ''),
                    'review_date': order_date
                }
                
                # Route review to appropriate list based on score
                if float(row['review_score']) < 4:
                    low_reviews.append(review_data)
                else:
                    high_reviews.append(review_data)
                    
        return low_reviews, high_reviews
    
    def _get_sentiment(self, score):
        """Convert review score to sentiment label"""
        if score >= 4:
            return 'Positive'
        elif score <= 2:
            return 'Negative'
        return 'Neutral'    
    
    def _bulk_upsert(self, documents, collection_name):
        """
        Perform bulk upsert operations
        
        Args:
            documents: List of documents to upsert
            collection_name: Name of collection to insert into
        """
        if not documents:
            return
        
        # Prepare bulk operations for low db
        try:
            bulk_operations = []
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
                
                # Create PyMongo-compatible update operation
                bulk_operations.append(
                    UpdateOne(
                        filter_query,
                        {'$set': doc},
                        upsert=True
                    )
                )
                
            # Execute bulk operations on both databases
            if bulk_operations:
                self.low_db[collection_name].bulk_write(bulk_operations, ordered=False)
                self.high_db[collection_name].bulk_write(bulk_operations, ordered=False)
                
        except BulkWriteError as bwe:
            logger.warning(f"Bulk write error for {collection_name}: {bwe.details}")
        except Exception as e:
            logger.error(f"Error in bulk upsert for {collection_name}: {str(e)}")
            raise
            
    def _bulk_insert(self, documents, collection_name, db=None):
        """
        Perform bulk insert operations
        
        Args:
            documents: List of documents to insert
            collection_name: Name of collection to insert into
            db: Database to insert into (defaults to both)
        """
        if not documents:
            return
            
        try:
            # If db not specified, use both
            if db is None:
                self.low_db[collection_name].insert_many(documents, ordered=False)
                self.high_db[collection_name].insert_many(documents, ordered=False)
            else:
                db[collection_name].insert_many(documents, ordered=False)
        except Exception as e:
            if "BulkWriteError" in str(e):
                logger.warning(f"Bulk write error for {collection_name}: {str(e)}")
            else:
                logger.error(f"Error in bulk insert for {collection_name}: {str(e)}")
                # Don't raise to allow processing to continue
    
    def _update_upload_status(self, upload_id, update_data):
        """
        Update the upload record status in both databases
        
        Args:
            upload_id: ID of the upload record 
            update_data: Data to update
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
            
            logger.info(f"Updated upload status: {update_data}")
        except Exception as e:
            logger.error(f"Error updating upload status: {str(e)}")


# Helper function to process analytics in background
def process_analytics_in_background(sales_data):
    """
    Process analytics data in background after initial data upload is complete.
    Generates data for all analytical collections:
    - sales_trends
    - product_performance
    - category_performance
    - demographics
    - geographical_insights
    - customer_behavior
    - predictions
    
    Args:
        sales_data: DataFrame containing sales data for analytics
    """
    try:
        # Make sure sales_data has datetime values for order_date/sale_date
        if 'order_date' in sales_data.columns:
            sales_data['order_date'] = pd.to_datetime(sales_data['order_date'])
        if 'sale_date' in sales_data.columns:
            sales_data['sale_date'] = pd.to_datetime(sales_data['sale_date'])
        
        # Get database connections
        low_db = get_db('low_review_score_db')
        high_db = get_db('high_review_score_db')
        
        # Import necessary models
        from analytics.models import (SalesTrend, ProductPerformance, CategoryPerformance,
                                     Demographics, GeographicalInsights, CustomerBehavior, 
                                     Prediction)
        import uuid
        from collections import defaultdict
            
        # --- SALES TRENDS ---
        logger.info("Generating sales trends data...")
        
        try:
            # Create monthly trends
            # Make sure we set the date as index
            date_col = 'sale_date' if 'sale_date' in sales_data.columns else 'order_date'
            df_copy = sales_data.copy()
            df_copy[date_col] = pd.to_datetime(df_copy[date_col])
            df_indexed = df_copy.set_index(date_col)
              # Monthly trends - use ME instead of M for month end
            # Use a simpler aggregation approach that doesn't rely on original DataFrame indices
            monthly_sales = df_indexed.resample('ME').agg({
                'quantity': 'sum'
            }).reset_index()
            
            # Calculate the total sales per month separately
            df_copy['total'] = df_copy['quantity'] * df_copy['price']
            monthly_totals = df_copy.set_index(date_col)['total'].resample('ME').sum().reset_index()
            monthly_sales['total_sales'] = monthly_totals['total']
              # Calculate growth rates
            monthly_sales['sales_growth_rate'] = monthly_sales['total_sales'].pct_change() * 100
            monthly_sales.fillna({'sales_growth_rate': 0}, inplace=True)
            
            # Calculate percentage of total
            total_sales = monthly_sales['total_sales'].sum()
            monthly_sales['sales_percentage'] = (monthly_sales['total_sales'] / total_sales) * 100 if total_sales > 0 else 0
            
            # Insert monthly trends
            sales_trends = []
            for idx, row in monthly_sales.iterrows():
                period_value = row[date_col].strftime('%Y-%m')
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
                
                # Insert into both DBs
                low_db.sales_trends.update_one({'id': trend_id}, {'$set': trend}, upsert=True)
                high_db.sales_trends.update_one({'id': trend_id}, {'$set': trend}, upsert=True)
            
            logger.info(f"Generated {len(monthly_sales)} monthly sales trend records")
              # Weekly trends - use the same approach as monthly
            weekly_sales = df_indexed.resample('W').agg({
                'quantity': 'sum'
            }).reset_index()
              # Calculate the total sales per week separately
            weekly_totals = df_copy.set_index(date_col)['total'].resample('W').sum().reset_index()
            weekly_sales['total_sales'] = weekly_totals['total']
            weekly_sales['sales_growth_rate'] = weekly_sales['total_sales'].pct_change() * 100
            weekly_sales.fillna({'sales_growth_rate': 0}, inplace=True)
            
            total_sales = weekly_sales['total_sales'].sum()
            weekly_sales['sales_percentage'] = (weekly_sales['total_sales'] / total_sales) * 100 if total_sales > 0 else 0
            
            for idx, row in weekly_sales.iterrows():
                week_num = row[date_col].isocalendar()[1]
                period_value = f"{row[date_col].year}-W{week_num:02d}"
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
                
                # Insert into both DBs
                low_db.sales_trends.update_one({'id': trend_id}, {'$set': trend}, upsert=True)
                high_db.sales_trends.update_one({'id': trend_id}, {'$set': trend}, upsert=True)
            
            logger.info(f"Generated a total of {len(sales_trends)} sales trend records")
        except Exception as e:
            logger.error(f"Error processing sales trends: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
        
        # --- CUSTOMER BEHAVIOR ---
        logger.info("Processing customer behavior data...")
        
        try:
            # Ensure we have the date column as datetime
            date_col = 'sale_date' if 'sale_date' in sales_data.columns else 'order_date'
            df_copy = sales_data.copy()
            df_copy[date_col] = pd.to_datetime(df_copy[date_col])
            
            # Group by customer to calculate purchases and spending
            customer_data = df_copy.groupby('customer_id').agg({
                date_col: 'count',  # Count purchases
                'price': lambda x: (df_copy.loc[x.index, 'quantity'] * x).sum() if not x.empty else 0
            }).reset_index()
            
            customer_data.rename(columns={date_col: 'total_purchases', 'price': 'total_spent'}, inplace=True)
            
            # Calculate purchase frequency
            if len(df_copy) > 0:
                min_date = df_copy[date_col].min()
                max_date = df_copy[date_col].max()
                
                # Calculate months difference
                if hasattr(min_date, 'year') and hasattr(max_date, 'year'):
                    months_diff = (max_date.year - min_date.year) * 12 + (max_date.month - min_date.month)
                    months_diff = max(1, months_diff)  # Ensure at least 1 month
                else:
                    months_diff = 1
            else:
                months_diff = 1
            
            # Calculate purchase frequency and segment customers
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
            
            # Create and insert documents
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
                
                # Insert into both DBs
                low_db.customer_behavior.update_one({'id': behavior_id}, {'$set': behavior}, upsert=True)
                high_db.customer_behavior.update_one({'id': behavior_id}, {'$set': behavior}, upsert=True)
            
            logger.info(f"Generated {len(customer_behaviors)} customer behavior records")
        except Exception as e:
            logger.error(f"Error processing customer behavior: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
        
        # --- GENERATE OTHER ANALYTICAL DATA IF NEEDED ---
        # Other analytical collections could be added here
        
        logger.info("Successfully processed analytics in background")
    except Exception as e:
        logger.error(f"Error processing analytics in background: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
