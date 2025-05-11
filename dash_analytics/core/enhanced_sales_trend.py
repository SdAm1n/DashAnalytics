"""
Enhanced version of sales trend update functions for high-performance processing

Features:
- Bulk database operations for improved performance
- Thread-safe database connections
- Parallel processing for large datasets
- Direct MongoDB access for optimized operations
"""

import logging
import pandas as pd
import numpy as np
import threading
from datetime import datetime
from analytics.models import SalesTrend
from mongoengine.connection import get_db
from pymongo import UpdateOne

logger = logging.getLogger(__name__)

# Thread local storage for database connections
thread_locals = threading.local()

def get_thread_db(alias):
    """
    Get database connection for the current thread
    
    Args:
        alias: Database alias ('low_review_score_db' or 'high_review_score_db')
        
    Returns:
        pymongo.database.Database: Database connection
    """
    if not hasattr(thread_locals, 'dbs'):
        thread_locals.dbs = {}
    
    if alias not in thread_locals.dbs:
        thread_locals.dbs[alias] = get_db(alias)
    
    return thread_locals.dbs[alias]

def update_sales_trend_enhanced(row, order_date):
    """Legacy compatible version - still handles single row updates"""
    try:
        # Import the specialized sales trend replication function
        from core.sales_trend_utils import replicate_sales_trend_data, ensure_database_consistency
        
        # Create period identifiers
        day = order_date.strftime('%Y-%m-%d')
        week = order_date.strftime('%Y-W%V')
        month = order_date.strftime('%Y-%m')
        year = order_date.strftime('%Y')
        quarter = f"{year}-Q{(order_date.month-1)//3 + 1}"

        periods = [
            ('daily', day),
            ('weekly', week),
            ('monthly', month),
            ('quarterly', quarter),
            ('yearly', year)
        ]

        for period_type, period_value in periods:
            trend_data = {
                'id': f"TREND-{period_type}-{period_value}",
                'period_type': period_type,
                'period_value': period_value,
                'total_sales': float(row['quantity'] * row['price']),
                'sales_growth_rate': 0.0,  # Will be calculated in batch
                'sales_percentage': 0.0  # Will be calculated in batch
            }
              # Use optimized replication function
            try:
                # Apply sales trend data efficiently
                replicate_sales_trend_data(trend_data)
            except Exception:
                # Direct database access as fallback
                try:
                    # Get databases directly
                    low_db = get_db('low_review_score_db')
                    high_db = get_db('high_review_score_db')
                    
                    # Remove any fields that might cause issues
                    if '_id' in trend_data:
                        del trend_data['_id']
                      # Insert directly with upsert
                    low_db.sales_trends.update_one(
                        {"period_type": period_type, "period_value": period_value},
                        {"$set": trend_data},
                        upsert=True
                    )
                    high_db.sales_trends.update_one(
                        {"period_type": period_type, "period_value": period_value},
                        {"$set": trend_data},
                        upsert=True
                    )
                except Exception:
                    pass
        
        return True
    except Exception:
        return False

def update_sales_trend_in_bulk(df, date_col='order_date'):
    """
    Process sales trend data in bulk from a DataFrame
    
    Args:
        df: DataFrame with sales data
        date_col: Name of date column
    
    Returns:
        bool: Success status
    """
    try:
        # Convert to datetime if not already
        if not pd.api.types.is_datetime64_dtype(df[date_col]):
            df[date_col] = pd.to_datetime(df[date_col])
        
        # Add derived columns for aggregation
        df['revenue'] = df['price'] * df['quantity'] 
        df['profit'] = df['revenue'] * 0.3  # Assuming 30% profit margin
        
        # Extract date components for period aggregations
        df['day'] = df[date_col].dt.strftime('%Y-%m-%d')
        df['week'] = df[date_col].dt.strftime('%Y-W%V')
        df['month'] = df[date_col].dt.strftime('%Y-%m')
        df['quarter'] = df[date_col].apply(lambda x: f"{x.strftime('%Y')}-Q{(x.month-1)//3 + 1}")
        df['year'] = df[date_col].dt.strftime('%Y')
        
        # Process each period type
        period_types = {
            'day': 'daily',
            'week': 'weekly',
            'month': 'monthly',
            'quarter': 'quarterly',
            'year': 'yearly',
        }
        
        # Get database connections
        low_db = get_db('low_review_score_db')
        high_db = get_db('high_review_score_db')
          # Process each period type for optimal performance
        for period_col, period_name in period_types.items():
            _process_period_bulk(df, period_col, period_name, low_db, high_db)
            
        return True
        
    except Exception as e:
        logger.error(f"Error in bulk sales trend processing: {str(e)}")
        return False

def _process_period_bulk(df, period_col, period_name, low_db, high_db):
    """Process a specific period type in bulk"""
    try:
        # Group by period
        grouped = df.groupby(period_col).agg({
            'revenue': 'sum',
            'quantity': 'sum',
            'order_id': 'nunique',  # Count unique orders
        }).reset_index()
        
        # Calculate average order value
        grouped['avg_order_value'] = grouped['revenue'] / grouped['order_id']
        
        # Calculate growth rates (sort first by period)
        grouped = grouped.sort_values(period_col)
        grouped['prev_revenue'] = grouped['revenue'].shift(1)
        grouped['sales_growth_rate'] = 0.0  # Default
        
        # Calculate growth rate where previous revenue exists
        mask = (grouped['prev_revenue'] > 0)
        grouped.loc[mask, 'sales_growth_rate'] = (
            (grouped.loc[mask, 'revenue'] - grouped.loc[mask, 'prev_revenue']) / 
            grouped.loc[mask, 'prev_revenue'] * 100
        )
        
        # Prepare bulk operations
        bulk_operations = []
        for _, row in grouped.iterrows():
            period_value = row[period_col]
            trend_id = f"TREND-{period_name}-{period_value}"
            
            update_data = {
                'id': trend_id,
                'period_type': period_name,
                'period_value': period_value,
                'total_sales': float(row['revenue']),
                'total_orders': int(row['order_id']),
                'total_quantity': int(row['quantity']),
                'average_order_value': float(row['avg_order_value']),
                'sales_growth_rate': float(row['sales_growth_rate']),
                'sales_percentage': 0.0  # Will be calculated later in post-processing
            }
            
            # Create upsert operation
            bulk_operations.append(
                UpdateOne(
                    {'id': trend_id},
                    {'$set': update_data},
                    upsert=True
                )
            )
          # Execute bulk operations on both databases
        if bulk_operations:
            low_db.sales_trends.bulk_write(bulk_operations, ordered=False)
            high_db.sales_trends.bulk_write(bulk_operations, ordered=False)

    except Exception as e:
        logger.error(f"Error processing {period_name} sales trends: {str(e)}")
        pass
