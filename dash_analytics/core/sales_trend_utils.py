"""
Sales trend specific utility functions to ensure proper replication of all period types
(daily, weekly, monthly, quarterly, yearly) between databases.
"""

import logging
from datetime import datetime
from analytics.models import SalesTrend

logger = logging.getLogger(__name__)

def replicate_sales_trend_data(data):
    """
    Specialized replication function for sales trend data that ensures all period types
    (daily, weekly, monthly, quarterly, yearly) are properly replicated across both databases.
    
    This function directly handles the SalesTrend model case to ensure consistency.
    """
    try:
        # Extract period type for logging
        period_type = data.get('period_type', 'unknown')
        period_value = data.get('period_value', 'unknown')
        
        # If no ID provided, generate one based on period
        if 'id' not in data:
            data['id'] = f"TREND-{period_type}-{period_value}"
            
        # Make a copy to avoid reference issues
        data_copy = data.copy()
        
        # Force logging to trace the issue
        logger.info(f"Replicating {period_type} trend for {period_value} with ID {data_copy['id']}")
        
        # First save to low_review_score_db with explicit handling for each period type
        try:
            # Use the custom method for creating/updating by unique fields
            low_doc = SalesTrend.objects(
                period_type=data_copy['period_type'], 
                period_value=data_copy['period_value']
            ).using('low_review_score_db').first()
            
            if low_doc:
                # Update existing document
                for key, value in data_copy.items():
                    if key != 'id':  # Skip the ID field
                        setattr(low_doc, key, value)
                # Explicitly force save to low_review_score_db
                low_doc.switch_db('low_review_score_db')
                low_doc.save()
                logger.info(f"Updated existing {period_type} trend in low_review_score_db")
            else:
                # Create new document with explicit DB selection
                low_doc = SalesTrend(**data_copy)
                # Force database selection for new document
                low_doc.switch_db('low_review_score_db')
                low_doc.save()
                logger.info(f"Created new {period_type} trend in low_review_score_db with ID {low_doc.id}")
                
            logger.info(f"Successfully saved {period_type} trend for {period_value} to low_review_score_db")
        except Exception as e:
            logger.error(f"Error saving {period_type} trend for {period_value} to low_review_score_db: {str(e)}")
            # Try a more direct approach if the first method fails
            try:
                # Get the database directly
                from mongoengine.connection import get_db
                db = get_db('low_review_score_db')
                # Clean data for MongoDB insertion
                mongo_data = data_copy.copy()
                # Insert directly into the collection
                db.sales_trends.update_one(
                    {"period_type": period_type, "period_value": period_value},
                    {"$set": mongo_data},
                    upsert=True
                )
                logger.info(f"Used direct MongoDB insertion for {period_type} in low_review_score_db")
                # Retrieve the document we just created/updated
                low_doc = SalesTrend.objects(
                    period_type=period_type, 
                    period_value=period_value
                ).using('low_review_score_db').first()
            except Exception as direct_err:            
                logger.error(f"Direct insertion also failed: {str(direct_err)}")
                low_doc = None

        # Then save to high_review_score_db
        try:
            # Use the custom method for creating/updating by unique fields
            high_doc = SalesTrend.objects(
                period_type=data_copy['period_type'], 
                period_value=data_copy['period_value']
            ).using('high_review_score_db').first()
            
            if high_doc:
                # Update existing document
                for key, value in data_copy.items():
                    if key != 'id':  # Skip the ID field
                        setattr(high_doc, key, value)
                # Explicitly force save to high_review_score_db
                high_doc.switch_db('high_review_score_db')
                high_doc.save()
                logger.info(f"Updated existing {period_type} trend in high_review_score_db")
            else:
                # Create new document with explicit DB selection
                high_doc = SalesTrend(**data_copy)
                if low_doc and low_doc.id:
                    high_doc.id = low_doc.id  # Use the same ID for consistency
                # Force database selection for new document
                high_doc.switch_db('high_review_score_db')
                high_doc.save()
                logger.info(f"Created new {period_type} trend in high_review_score_db with ID {high_doc.id}")
                
            logger.info(f"Successfully saved {period_type} trend for {period_value} to high_review_score_db")
        except Exception as e:
            logger.error(f"Error saving {period_type} trend for {period_value} to high_review_score_db: {str(e)}")
            # Try a more direct approach if the first method fails
            try:
                from mongoengine.connection import get_db
                db = get_db('high_review_score_db')
                # Clean data for MongoDB insertion
                mongo_data = data_copy.copy()
                # Insert directly into the collection
                db.sales_trends.update_one(
                    {"period_type": period_type, "period_value": period_value},
                    {"$set": mongo_data},
                    upsert=True
                )
                logger.info(f"Used direct MongoDB insertion for {period_type} in high_review_score_db")
                high_doc = SalesTrend.objects(
                    period_type=period_type, 
                    period_value=period_value
                ).using('high_review_score_db').first()
            except Exception as direct_err:
                logger.error(f"Direct insertion also failed: {str(direct_err)}")
                high_doc = None
        
        # Finally, verify that both documents exist and are consistent
        if low_doc and high_doc:
            logger.info(f"Successfully replicated {period_type} trend for {period_value} in both databases")
        else:
            logger.warning(f"Partial success: low_doc={bool(low_doc)}, high_doc={bool(high_doc)}")
            
        return low_doc, high_doc
    except Exception as e:
        logger.error(f"Error in replicate_sales_trend_data: {str(e)}")
        return None, None

def update_all_sales_trends():
    """
    Update and ensure replication of all sales trend records.
    This function is intended to be used once to fix the replication issue.
    """
    try:
        # Import for direct MongoDB access if needed
        from mongoengine.connection import get_db
        
        # Get databases directly
        low_db = get_db('low_review_score_db')
        high_db = get_db('high_review_score_db')
        
        # Check counts before fix
        low_count_before = low_db.sales_trends.count_documents({})
        high_count_before = high_db.sales_trends.count_documents({})
        logger.info(f"Before fix: low_db has {low_count_before} records, high_db has {high_count_before} records")
        
        # Check period type distribution before fix
        low_period_types = {}
        for period_type in ['daily', 'weekly', 'monthly', 'quarterly', 'yearly']:
            count = low_db.sales_trends.count_documents({"period_type": period_type})
            low_period_types[period_type] = count
        
        logger.info(f"Period types in low_db before fix: {low_period_types}")
        
        # Ensure we have direct DB copy as a backup if there are significant differences
        if high_count_before > low_count_before * 1.5 or any(
            low_period_types.get(period, 0) == 0 and 
            (period != 'monthly') for period in ['daily', 'weekly', 'quarterly', 'yearly']
        ):
            logger.warning("Detected significant differences between databases or missing period types")
            logger.info("Performing direct database copy for all missing period types")
            direct_db_copy()
            
        # Get all sales trends from high_review_score_db
        high_trends = list(SalesTrend.objects.using('high_review_score_db').all())
        fixed_count = 0
        
        # Process period types in a specific order to ensure consistency
        period_types_order = ['monthly', 'daily', 'weekly', 'quarterly', 'yearly']
        for period_type in period_types_order:
            filtered_trends = [t for t in high_trends if t.period_type == period_type]
            logger.info(f"Processing {len(filtered_trends)} {period_type} records")
            
            for high_trend in filtered_trends:
                # Convert MongoDB document to Python dict
                data = {
                    'id': high_trend.id,
                    'period_type': high_trend.period_type,
                    'period_value': high_trend.period_value,
                    'total_sales': high_trend.total_sales,
                    'sales_growth_rate': high_trend.sales_growth_rate,
                    'sales_percentage': high_trend.sales_percentage
                }
                
                # Check if this document exists in low_review_score_db
                low_trend = SalesTrend.objects(
                    period_type=high_trend.period_type,
                    period_value=high_trend.period_value
                ).using('low_review_score_db').first()
                
                # Always ensure replication for all period types, not just non-monthly
                if not low_trend or True:  # Force replication for all records
                    low_doc, high_doc = replicate_sales_trend_data(data)
                    if low_doc and high_doc:
                        fixed_count += 1
                        logger.info(f"Fixed {high_trend.period_type} record for {high_trend.period_value}")
        
        # Check counts after fix
        low_count_after = low_db.sales_trends.count_documents({})
        high_count_after = high_db.sales_trends.count_documents({})
        logger.info(f"After fix: low_db has {low_count_after} records, high_db has {high_count_after} records")
        
        # Check period type distribution after fix
        low_period_types_after = {}
        for period_type in ['daily', 'weekly', 'monthly', 'quarterly', 'yearly']:
            count = low_db.sales_trends.count_documents({"period_type": period_type})
            low_period_types_after[period_type] = count
        
        logger.info(f"Period types in low_db after fix: {low_period_types_after}")
        
        logger.info(f"Fixed {fixed_count} sales trend records")
        return fixed_count
    except Exception as e:
        logger.error(f"Error in update_all_sales_trends: {str(e)}")
        return 0

def direct_db_copy(from_db='high_review_score_db', to_db='low_review_score_db', period_types=None):
    """
    Directly copy sales trend records from one database to another using PyMongo
    This bypasses the ORM layer to ensure consistent replication
    
    Args:
        from_db: Source database (default: high_review_score_db)
        to_db: Target database (default: low_review_score_db)
        period_types: List of period types to copy, or None for all (default: None)
    """
    try:
        from mongoengine.connection import get_db
        
        # Get database connections
        source_db = get_db(from_db)
        target_db = get_db(to_db)
        
        # Filter by period types if specified
        query = {}
        if period_types:
            query["period_type"] = {"$in": period_types}
            
        # Get all records from source with the query
        source_records = list(source_db.sales_trends.find(query))
        logger.info(f"Found {len(source_records)} records in {from_db} {' for selected period types' if period_types else ''}")
        
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
        
        logger.info(f"Successfully copied {success_count} records from {from_db} to {to_db}")
        return success_count
    except Exception as e:
        logger.error(f"Error in direct_db_copy: {str(e)}")
        return 0

def ensure_database_consistency(period_type, period_value):
    """
    Forcefully ensure sales trend data consistency between databases for a specific period.
    This function checks if a record exists in one database but not the other and copies it.
    """
    try:
        # Get database connections directly
        from mongoengine.connection import get_db
        low_db = get_db('low_review_score_db')
        high_db = get_db('high_review_score_db')
        
        # Check if record exists in high_review_score_db through direct pymongo
        high_doc_direct = high_db.sales_trends.find_one({
            "period_type": period_type,
            "period_value": period_value
        })
        
        # Check if record exists in low_review_score_db through direct pymongo
        low_doc_direct = low_db.sales_trends.find_one({
            "period_type": period_type,
            "period_value": period_value
        })
        
        # Also check through MongoEngine for logging
        high_doc = SalesTrend.objects(
            period_type=period_type, 
            period_value=period_value
        ).using('high_review_score_db').first()
        
        # Check if record exists in low_review_score_db
        low_doc = SalesTrend.objects(
            period_type=period_type, 
            period_value=period_value
        ).using('low_review_score_db').first()
        
        if high_doc and not low_doc:
            # Copy from high to low
            logger.info(f"Copying {period_type} trend for {period_value} from high_db to low_db")
            
            # Convert the document to a dictionary
            data = {
                'id': high_doc.id,
                'period_type': high_doc.period_type,
                'period_value': high_doc.period_value,
                'total_sales': high_doc.total_sales,
                'sales_growth_rate': high_doc.sales_growth_rate,
                'sales_percentage': high_doc.sales_percentage
            }
            
            # Create new document in low_db
            new_low_doc = SalesTrend(**data)
            new_low_doc.switch_db('low_review_score_db')
            new_low_doc.save()
            logger.info(f"Successfully copied {period_type} trend to low_db")
            
            return True
            
        elif low_doc and not high_doc:
            # Copy from low to high
            logger.info(f"Copying {period_type} trend for {period_value} from low_db to high_db")
            
            # Convert the document to a dictionary
            data = {
                'id': low_doc.id,
                'period_type': low_doc.period_type,
                'period_value': low_doc.period_value,
                'total_sales': low_doc.total_sales,
                'sales_growth_rate': low_doc.sales_growth_rate,
                'sales_percentage': low_doc.sales_percentage
            }
            
            # Create new document in high_db
            new_high_doc = SalesTrend(**data)
            new_high_doc.switch_db('high_review_score_db')
            new_high_doc.save()
            logger.info(f"Successfully copied {period_type} trend to high_db")
            
            return True
            
        elif high_doc and low_doc:
            # Both exist, but might have different data - sync them
            logger.info(f"Syncing {period_type} trend for {period_value} between databases")
            
            # Take the high_db version as source of truth and update low_db version
            low_doc.total_sales = high_doc.total_sales
            low_doc.sales_growth_rate = high_doc.sales_growth_rate
            low_doc.sales_percentage = high_doc.sales_percentage
            low_doc.save()
            
            logger.info(f"Successfully synced {period_type} trend between databases")
            return True
            
        else:
            # Neither exists - nothing to do
            logger.warning(f"No {period_type} trend for {period_value} found in either database")
            return False
            
    except Exception as e:
        logger.error(f"Error in ensure_database_consistency for {period_type} {period_value}: {str(e)}")
        return False
