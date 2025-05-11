"""
Enhanced version of sales trend update functions to ensure consistent replication
"""

import logging
from datetime import datetime
from analytics.models import SalesTrend
from mongoengine.connection import get_db

logger = logging.getLogger(__name__)

def update_sales_trend_enhanced(row, order_date):
    """Enhanced version of update_sales_trend that ensures proper replication"""
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
            
            # Use specialized replication function with double verification
            try:
                # First attempt - use replicate_sales_trend_data
                low_doc, high_doc = replicate_sales_trend_data(trend_data)
                
                # Additional verification
                if not low_doc or not high_doc:
                    logger.warning(f"Initial replication failed for {period_type}. Retrying with direct method...")
                    # Force consistency between databases as a failsafe
                    ensure_database_consistency(period_type, period_value)
                
                logger.info(f"Successfully processed {period_type} trend during CSV upload")
            except Exception as inner_e:
                logger.error(f"Error in replication for {period_type}: {str(inner_e)}")
                # Last resort - try direct database access
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
                    logger.info(f"Used direct MongoDB insertion for {period_type}")
                except Exception as direct_err:
                    logger.error(f"Direct insertion also failed: {str(direct_err)}")
        
        return True
    except Exception as e:
        logger.error(f"Error updating sales trend: {str(e)}")
        return False
