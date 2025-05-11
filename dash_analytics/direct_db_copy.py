"""
Direct Sales Trend Database Fix 

This script directly copies all sales trends between databases
using PyMongo direct database access, bypassing the MongoEngine ORM.
Use this when other methods have failed to fix specific record types.
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
        logging.FileHandler(f"direct_copy_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    ]
)
logger = logging.getLogger(__name__)

# Import models after Django setup
from analytics.models import SalesTrend
from mongoengine.connection import get_db

def direct_db_copy(from_db='high_review_score_db', to_db='low_review_score_db'):
    """
    Directly copy all sales trend records from one database to another using PyMongo
    This is a last resort when other methods fail
    """
    try:
        # Get database connections
        source_db = get_db(from_db)
        target_db = get_db(to_db)
        
        # Get all records from source
        source_records = list(source_db.sales_trends.find({}))
        logger.info(f"Found {len(source_records)} records in {from_db}")
        
        # Get period type counts before copy
        period_types_before = {}
        for period_type in ['daily', 'weekly', 'monthly', 'quarterly', 'yearly']:
            count = target_db.sales_trends.count_documents({"period_type": period_type})
            period_types_before[period_type] = count
        
        logger.info(f"Target DB period types before copy: {period_types_before}")
        
        # Copy to target - upsert to avoid duplicates
        success_count = 0
        for record in source_records:
            period_type = record.get('period_type', 'unknown')
            period_value = record.get('period_value', 'unknown')
            record_id = record.get('_id')  # Save the ID
            record_copy = record.copy()
            
            # Remove MongoDB specific fields
            if '_id' in record_copy:
                del record_copy['_id']
                
            try:
                # Use period_type and period_value as unique keys
                result = target_db.sales_trends.update_one(
                    {
                        'period_type': period_type,
                        'period_value': period_value
                    },
                    {'$set': record_copy},
                    upsert=True
                )
                
                if result.modified_count > 0 or result.upserted_id:
                    success_count += 1
                    logger.info(f"Successfully copied {period_type} record for {period_value}")
            except Exception as e:
                logger.error(f"Error copying {period_type} record for {period_value}: {str(e)}")
        
        # Get period type counts after copy
        period_types_after = {}
        for period_type in ['daily', 'weekly', 'monthly', 'quarterly', 'yearly']:
            count = target_db.sales_trends.count_documents({"period_type": period_type})
            period_types_after[period_type] = count
        
        logger.info(f"Target DB period types after copy: {period_types_after}")
        
        # Calculate records added by type
        added_by_type = {}
        for period_type in period_types_after.keys():
            added = period_types_after[period_type] - period_types_before.get(period_type, 0)
            added_by_type[period_type] = added
        
        logger.info(f"Records added by period type: {added_by_type}")
        logger.info(f"Total: Successfully copied {success_count} records from {from_db} to {to_db}")
        
        return success_count
    except Exception as e:
        logger.error(f"Error in direct_db_copy: {str(e)}")
        return 0

def verify_databases():
    """Verify that both databases have the same sales trend records"""
    try:
        # Get database connections
        low_db = get_db('low_review_score_db')
        high_db = get_db('high_review_score_db')
        
        # Get all records from both databases
        low_count = low_db.sales_trends.count_documents({})
        high_count = high_db.sales_trends.count_documents({})
        
        logger.info(f"Low DB has {low_count} records, High DB has {high_count} records")
        
        # Check period type distribution
        low_period_types = {}
        high_period_types = {}
        for period_type in ['daily', 'weekly', 'monthly', 'quarterly', 'yearly']:
            low_count = low_db.sales_trends.count_documents({"period_type": period_type})
            high_count = high_db.sales_trends.count_documents({"period_type": period_type})
            low_period_types[period_type] = low_count
            high_period_types[period_type] = high_count
        
        logger.info(f"Low DB period types: {low_period_types}")
        logger.info(f"High DB period types: {high_period_types}")
        
        # Check for specific records
        if low_count != high_count:
            logger.warning("Databases have different record counts!")
            
            # Find records in high_db that aren't in low_db
            high_records = list(high_db.sales_trends.find({}, {"period_type": 1, "period_value": 1}))
            missing_in_low = 0
            
            for record in high_records:
                period_type = record.get('period_type', '')
                period_value = record.get('period_value', '')
                
                # Check if this record exists in low_db
                low_record = low_db.sales_trends.find_one({
                    "period_type": period_type,
                    "period_value": period_value
                })
                
                if not low_record:
                    missing_in_low += 1
                    if missing_in_low <= 5:  # Show only first 5
                        logger.warning(f"Missing in low_db: {period_type} - {period_value}")
            
            logger.warning(f"Total records missing in low_db: {missing_in_low}")
            
        else:
            logger.info("Both databases have the same number of records")
            
            # Still check for any inconsistencies in period types
            for period_type in low_period_types.keys():
                if low_period_types[period_type] != high_period_types.get(period_type, 0):
                    logger.warning(f"Inconsistency in {period_type} counts: " 
                                  f"Low={low_period_types[period_type]}, " 
                                  f"High={high_period_types.get(period_type, 0)}")
                
            if low_period_types == high_period_types:
                logger.info("SUCCESS: Both databases have identical period type distributions!")
                return True
        
        return False
    except Exception as e:
        logger.error(f"Error in verify_databases: {str(e)}")
        return False

def clean_up_databases():
    """Remove any test records created during troubleshooting"""
    try:
        # Get database connections
        low_db = get_db('low_review_score_db')
        high_db = get_db('high_review_score_db')
        
        # Remove test records
        test_patterns = ["TEST", "TESTCHECK", "COMPREHENSIVE-TEST"]
        total_removed = 0
        
        for pattern in test_patterns:
            # Remove from low_db
            result_low = low_db.sales_trends.delete_many({"id": {"$regex": pattern}})
            removed_low = result_low.deleted_count
            
            # Remove from high_db 
            result_high = high_db.sales_trends.delete_many({"id": {"$regex": pattern}})
            removed_high = result_high.deleted_count
            
            total_removed += removed_low + removed_high
            logger.info(f"Removed {removed_low} test records from low_db and {removed_high} from high_db matching '{pattern}'")
        
        logger.info(f"Total test records removed: {total_removed}")
        return True
    except Exception as e:
        logger.error(f"Error in clean_up_databases: {str(e)}")
        return False

def main():
    """Run the direct sales trend database copy fix"""
    start_time = datetime.now()
    print("=" * 60)
    print("STARTING DIRECT SALES TREND DB COPY")
    print("=" * 60)
    logger.info("=" * 60)
    logger.info("STARTING DIRECT SALES TREND DB COPY")
    logger.info("=" * 60)
    
    try:
        # Step 1: Verify current database state
        print("Step 1: Verifying current database state...")
        logger.info("Step 1: Verifying current database state...")
        
        # Get database connections directly
        low_db = get_db('low_review_score_db')
        high_db = get_db('high_review_score_db')
        
        # Get all records from both databases
        low_count = low_db.sales_trends.count_documents({})
        high_count = high_db.sales_trends.count_documents({})
        
        print(f"Initial state: Low DB has {low_count} records, High DB has {high_count} records")
        
        # Check period type distribution
        low_period_types = {}
        high_period_types = {}
        for period_type in ['daily', 'weekly', 'monthly', 'quarterly', 'yearly']:
            low_count = low_db.sales_trends.count_documents({"period_type": period_type})
            high_count = high_db.sales_trends.count_documents({"period_type": period_type})
            low_period_types[period_type] = low_count
            high_period_types[period_type] = high_count
        
        print(f"Low DB period types: {low_period_types}")
        print(f"High DB period types: {high_period_types}")
        verify_databases()
        
        # Step 2: Clean up any test records first
        print("Step 2: Cleaning up test records...")
        logger.info("Step 2: Cleaning up test records...")
        clean_up_databases()
        
        # Step 3: Copy all sales trend records from high_db to low_db
        print("Step 3: Copying all sales trend records from high_db to low_db...")
        logger.info("Step 3: Copying all sales trend records from high_db to low_db...")
        copied_count = direct_db_copy('high_review_score_db', 'low_review_score_db')
        print(f"Copied {copied_count} records from high_db to low_db")
        logger.info(f"Copied {copied_count} records from high_db to low_db")
        
        # Step 4: Final verification
        print("Step 4: Performing final verification...")
        logger.info("Step 4: Performing final verification...")
        success = verify_databases()
        
        # Get final database state
        low_count_after = low_db.sales_trends.count_documents({})
        high_count_after = high_db.sales_trends.count_documents({})
        
        # Check period type distribution after
        low_period_types_after = {}
        high_period_types_after = {}
        for period_type in ['daily', 'weekly', 'monthly', 'quarterly', 'yearly']:
            low_count = low_db.sales_trends.count_documents({"period_type": period_type})
            high_count = high_db.sales_trends.count_documents({"period_type": period_type})
            low_period_types_after[period_type] = low_count
            high_period_types_after[period_type] = high_count
        
        print(f"AFTER FIX - Low DB period types: {low_period_types_after}")
        print(f"AFTER FIX - High DB period types: {high_period_types_after}")
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print("=" * 60)
        print("DIRECT SALES TREND DB COPY COMPLETE")
        print("=" * 60)
        print(f"Duration: {duration:.2f} seconds")
        print(f"Final result: {'SUCCESS' if success else 'ISSUES REMAIN'}")
        print("=" * 60)
        
        logger.info("=" * 60)
        logger.info("DIRECT SALES TREND DB COPY COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Duration: {duration:.2f} seconds")
        logger.info(f"Final result: {'SUCCESS' if success else 'ISSUES REMAIN'}")
        logger.info("=" * 60)
        
        return 0 if success else 1
        
    except Exception as e:
        error_msg = f"ERROR: {str(e)}"
        print(error_msg)
        logger.error(error_msg)
        return 1

if __name__ == "__main__":
    sys.exit(main())
