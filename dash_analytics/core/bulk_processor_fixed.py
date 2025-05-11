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
        Perform bulk upsert operations in both databases
        
        Args:
            documents: List of documents to insert/update
            collection_name: Name of collection to insert into
        """
        if not documents:
            return
        
        try:
            # Simple insert_many approach instead of bulk write with updateOne
            # Since we've already de-duped the data in the extract methods
            self.low_db[collection_name].insert_many(documents, ordered=False)
            self.high_db[collection_name].insert_many(documents, ordered=False)
        except Exception as e:
            if "duplicate key" in str(e):
                # For duplicates, fall back to individual upserts
                for doc in documents:
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
                    
                    try:
                        self.low_db[collection_name].update_one(
                            filter_query, {'$set': doc}, upsert=True
                        )
                        self.high_db[collection_name].update_one(
                            filter_query, {'$set': doc}, upsert=True
                        )
                    except Exception as inner_e:
                        logger.warning(f"Error upserting individual {collection_name} record: {str(inner_e)}")
            else:
                logger.error(f"Error in bulk upsert for {collection_name}: {str(e)}")
                # Don't raise to allow processing to continue
    
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
            if "duplicate key" in str(e):
                logger.warning(f"Duplicate keys found in {collection_name}, attempting individual inserts")
                # Fall back to individual inserts
                for doc in documents:
                    try:
                        if db is None:
                            self.low_db[collection_name].insert_one(doc)
                            self.high_db[collection_name].insert_one(doc)
                        else:
                            db[collection_name].insert_one(doc)
                    except Exception as inner_e:
                        if "duplicate key" not in str(inner_e):
                            logger.warning(f"Error inserting individual {collection_name} record: {str(inner_e)}")
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
