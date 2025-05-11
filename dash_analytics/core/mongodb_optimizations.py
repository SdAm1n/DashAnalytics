"""
MongoDB Connection Optimization Module

This module provides optimized MongoDB connection handling for improved performance in the DashAnalytics application.

Benefits:
- Connection pooling
- Connection reuse
- Optimized write operations
- Bulk operations support
"""

import logging
from mongoengine import connect
from pymongo import MongoClient
from django.conf import settings
from core.csv_processing_config import MONGODB_OPTIMIZATIONS

logger = logging.getLogger(__name__)

# Global connection pools
_connection_pools = {}


def get_optimized_connection(db_alias):
    """
    Get an optimized MongoDB connection from the connection pool
    
    Args:
        db_alias: Database alias name 
        
    Returns:
        pymongo.database.Database: Optimized database connection
    """
    global _connection_pools
    
    if db_alias not in _connection_pools:
        # Create new connection with optimized settings
        try:
            db_settings = settings.MONGODB_DATABASES.get(db_alias)
            if not db_settings:
                raise ValueError(f"MongoDB settings not found for alias: {db_alias}")
                
            # Configure connection pool size
            max_pool_size = MONGODB_OPTIMIZATIONS.get('CONNECTION_POOL_SIZE', 100)
            
            # Create client with optimized connection pool
            client = MongoClient(
                db_settings['uri'],
                maxPoolSize=max_pool_size,
                waitQueueTimeoutMS=1000,  # Wait 1 second for connection from pool
                socketTimeoutMS=30000,    # 30 second socket timeout
                connectTimeoutMS=5000,    # 5 second connect timeout
                retryWrites=True,         # Enable retryable writes
                appname="DashAnalytics"   # Application name for monitoring
            )
            
            # Get database
            db = client[db_settings['name']]
            _connection_pools[db_alias] = db
            
            logger.info(f"Created optimized MongoDB connection for {db_alias}")
            
        except Exception as e:
            logger.error(f"Failed to create optimized MongoDB connection for {db_alias}: {str(e)}")
            # Fall back to regular connection
            db = connect(
                db=settings.MONGODB_DATABASES[db_alias]['name'],
                host=settings.MONGODB_DATABASES[db_alias]['uri'],
                alias=db_alias
            ).get_db()
            _connection_pools[db_alias] = db
            
    return _connection_pools[db_alias]


def get_bulk_operation_options():
    """
    Get optimized options for bulk write operations
    
    Returns:
        dict: Options for bulk write operations
    """
    return {
        'ordered': MONGODB_OPTIMIZATIONS.get('ORDERED_WRITES', False),
        'bypass_document_validation': True,  # Faster but less safe
        'w': MONGODB_OPTIMIZATIONS.get('WRITE_CONCERN', 1)
    }


def create_optimized_indexes():
    """
    Creates optimized indexes for improved query performance
    """
    try:
        # Get database connections
        low_db = get_optimized_connection('low_review_score_db')
        high_db = get_optimized_connection('high_review_score_db')
        
        # Collections that need optimized indexes
        collections_to_optimize = [
            {
                'name': 'sales_trends',
                'indexes': [
                    [('period_type', 1), ('period_value', 1)],  # Compound index for period queries
                    [('total_sales', -1)],  # Index for sorting by sales
                ]
            },
            {
                'name': 'orders',
                'indexes': [
                    [('order_date', -1)],  # Index for date ranges
                    [('customer_id', 1), ('order_date', -1)],  # Index for customer orders
                ]
            },
            {
                'name': 'sales',
                'indexes': [
                    [('sale_date', -1)],  # Index for date-based queries
                    [('revenue', -1)],  # Index for revenue sorting
                ]
            }
        ]
        
        # Create indexes in both databases
        for db in [low_db, high_db]:
            for collection_config in collections_to_optimize:
                collection_name = collection_config['name']
                if collection_name in db.list_collection_names():
                    collection = db[collection_name]
                    
                    # Create each index
                    for index_spec in collection_config['indexes']:
                        try:
                            collection.create_index(index_spec, background=True)
                        except Exception as index_error:
                            logger.warning(f"Error creating index on {collection_name}: {str(index_error)}")
        
        logger.info("Successfully created optimized indexes")
        return True
        
    except Exception as e:
        logger.error(f"Error creating optimized indexes: {str(e)}")
        return False
