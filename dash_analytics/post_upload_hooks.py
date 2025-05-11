"""
CSV Upload Post-processing Hook for Sales Trend Data

This script provides hooks that should be called after CSV data uploads
to ensure proper replication of sales trend data across all databases
and for all period types (daily, weekly, monthly, quarterly, yearly).
"""

import os
import sys
import django
import logging
from datetime import datetime

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dash_analytics.settings')
django.setup()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f"csv_upload_hook_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    ]
)
logger = logging.getLogger(__name__)

# Import models after Django setup
from analytics.models import SalesTrend
from mongoengine.connection import get_db
from core.sales_trend_utils import direct_db_copy

def post_csv_upload_hook():
    """
    Hook function that should be called after a CSV upload completes.
    This ensures all sales trend data is properly replicated across databases.
    """
    logger.info("Running post-CSV upload hook for sales trend data...")
    
    # Get database connections
    low_db = get_db('low_review_score_db')
    high_db = get_db('high_review_score_db')
    
    # Check period type distribution
    low_period_types = {}
    high_period_types = {}
    missing_period_types = []
    
    for period_type in ['daily', 'weekly', 'monthly', 'quarterly', 'yearly']:
        low_count = low_db.sales_trends.count_documents({"period_type": period_type})
        high_count = high_db.sales_trends.count_documents({"period_type": period_type})
        
        low_period_types[period_type] = low_count
        high_period_types[period_type] = high_count
        
        # Check if this period type might be missing in low_db
        if high_count > 0 and low_count == 0:
            logger.warning(f"Missing period type in low_db: {period_type}")
            missing_period_types.append(period_type)
    
    logger.info(f"Low DB period types: {low_period_types}")
    logger.info(f"High DB period types: {high_period_types}")
    
    # If we have missing period types in low_db, replicate them
    if missing_period_types:
        logger.info(f"Replicating missing period types: {missing_period_types}")
        copied_count = direct_db_copy('high_review_score_db', 'low_review_score_db', missing_period_types)
        logger.info(f"Copied {copied_count} records for the missing period types")
    
    # Double-check to make sure all records are properly replicated
    verify_replication_completeness()
    
    return True

def verify_replication_completeness():
    """
    Verify that sales trend replication is complete for all period types.
    """
    # Get database connections
    low_db = get_db('low_review_score_db')
    high_db = get_db('high_review_score_db')
    
    # Get total counts
    low_count = low_db.sales_trends.count_documents({})
    high_count = high_db.sales_trends.count_documents({})
    
    # Check if total counts match
    if low_count != high_count:
        logger.warning(f"Total record counts don't match: low={low_count}, high={high_count}")
        logger.info("Running full replication to ensure consistency...")
        direct_db_copy()
    else:
        logger.info(f"Both databases have the same number of records: {low_count}")
    
    return True

def ensure_sales_trend_consistency():
    """
    Main function to ensure sales trend data consistency.
    Can be called directly or scheduled after uploads.
    """
    try:
        logger.info("Ensuring sales trend data consistency across databases...")
        
        # Run the post-upload hook
        post_csv_upload_hook()
        
        # Report success
        logger.info("Sales trend data consistency check completed successfully")
        return True
    except Exception as e:
        logger.error(f"Error ensuring sales trend consistency: {str(e)}")
        return False

if __name__ == "__main__":
    ensure_sales_trend_consistency()
