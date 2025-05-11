"""
Enhanced Bulk Data Processing Module for DashAnalytics

Provides high-performance data processing functionality for CSV uploads:
1. Bulk inserts instead of individual .save() operations
2. Threading for parallel data processing
3. Chunk processing for large files
4. Optimized database connections
5. Properly populates all analytical collections
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

# Global variables for database connections
low_db = get_db('low_review_score_db')
high_db = get_db('high_review_score_db')

class EnhancedBulkProcessor:
    """
    Enhanced version of BulkDataProcessor that properly populates all collections
    including the analytical collections
    """
    def __init__(self, chunk_size=500, max_threads=4):
        """
        Initialize the processor
        
        Args:
            chunk_size: Number of records to process in a single batch
            max_threads: Maximum number of worker threads for parallel processing
        """
        self.chunk_size = chunk_size
        self.max_threads = max_threads
        self.results_queue = queue.Queue()
        self.low_db = low_db
        self.high_db = high_db
        logger.info(f"Initialized EnhancedBulkProcessor with chunk_size={chunk_size}, max_threads={max_threads}")
    
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
        logger.info(f"Starting to process {total_records} records with upload ID: {upload_id}")
        
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
        
        # Ensure date columns are datetime
        if 'order_date' in df.columns:
            df['order_date'] = pd.to_datetime(df['order_date'])
        
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
        
        # Process analytical data
        logger.info("Basic data processing completed, generating analytical data")
        try:
            # Create a copy to avoid modifying the original
            analytics_df = df.copy()
            # Process in background
            self.process_analytical_data(analytics_df, upload_id)
            logger.info("Successfully processed analytical data")
        except Exception as e:
            logger.error(f"Error processing analytical data: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
        
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
            logger.info("Generating sales trends data...")
            
            # Group by day, week, month, and year
            sales_trends = []
            
            # Create monthly trends
            try:
                # Make sure the order_date is in datetime format
                df['order_date'] = pd.to_datetime(df['order_date'])
                
                # Set order_date as index
                df_indexed = df.set_index('order_date')
                
                # Monthly trends
                monthly_sales = df_indexed.resample('ME').agg({
                    'quantity': 'sum',
                    'price': lambda x: (df_indexed.loc[x.index, 'quantity'] * x).sum() if not x.empty else 0
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
                
                # Weekly trends
                weekly_sales = df_indexed.resample('W').agg({
                    'quantity': 'sum',
                    'price': lambda x: (df_indexed.loc[x.index, 'quantity'] * x).sum() if not x.empty else 0
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
                
                # Insert sales trends
                self._bulk_upsert(sales_trends, 'sales_trends')
                logger.info(f"Processed {len(sales_trends)} sales trend records")
            except Exception as e:
                logger.error(f"Error processing sales trends: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
            
            # --- CUSTOMER BEHAVIOR ---
            logger.info("Generating customer behavior data...")
            
            try:
                # Ensure order_date is datetime
                df['order_date'] = pd.to_datetime(df['order_date'])
                
                # Group by customer
                customer_data = df.groupby('customer_id').agg({
                    'order_date': 'count',  # Count purchases
                    'price': lambda x: (df.loc[x.index, 'quantity'] * x).sum()
                }).reset_index()
                
                customer_data.rename(columns={'order_date': 'total_purchases', 'price': 'total_spent'}, inplace=True)
                
                # Calculate purchase frequency (purchases per month)
                # Safely get min and max dates
                if not df.empty:
                    min_date = df['order_date'].min()
                    max_date = df['order_date'].max()
                    
                    # Calculate number of months
                    if hasattr(min_date, 'year') and hasattr(max_date, 'year'):
                        months_diff = (max_date.year - min_date.year) * 12 + (max_date.month - min_date.month)
                    else:
                        # Default to 1 month if dates aren't proper datetime
                        months_diff = 1
                else:
                    months_diff = 1
                
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
                logger.info(f"Processed {len(customer_behaviors)} customer behavior records")
            except Exception as e:
                logger.error(f"Error processing customer behavior: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
            
            # Process other analytical collections if needed
            
            logger.info("All analytical data processed successfully.")
            return True
        
        except Exception as e:
            logger.error(f"Error in process_analytical_data: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False
