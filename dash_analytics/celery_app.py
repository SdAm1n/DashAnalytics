"""
Celery Task Configuration for DashAnalytics

This module configures Celery for background processing tasks related to data uploads.
"""

import os
from celery import Celery
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dash_analytics.settings')

# Create Celery app
app = Celery('dash_analytics')

# Load configuration from Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Configure for development (use SQLite for result backend in development mode)
app.conf.update(
    broker_url='memory://',
    task_always_eager=True,  # For development - execute tasks immediately
    task_eager_propagates=True,  # Show exceptions when in eager mode
    result_backend='db+sqlite:///results.sqlite'  # Use SQLite for result backend in dev
)

# Auto-discover tasks from installed apps
app.autodiscover_tasks()

# Define Celery tasks
@app.task(bind=True)
def process_csv_data_task(self, upload_id, temp_file_path):
    """
    Background task for processing CSV data
    
    Args:
        upload_id: ID of upload record
        temp_file_path: Path to temp CSV file
    """
    import pandas as pd
    from mongoengine import connect, get_db
    from django.conf import settings
    from core.bulk_processor import BulkDataProcessor
    from core.bulk_sales_trend import update_sales_trend_in_bulk
    
    try:
        # Ensure database connections
        connect(
            db=settings.MONGODB_DATABASES['low_review_score_db']['name'],
            host=settings.MONGODB_DATABASES['low_review_score_db']['uri'],
            alias='low_review_score_db'
        )
        connect(
            db=settings.MONGODB_DATABASES['high_review_score_db']['name'],
            host=settings.MONGODB_DATABASES['high_review_score_db']['uri'],
            alias='high_review_score_db'
        )
        
        # Read CSV file
        df = pd.read_csv(temp_file_path)
        
        # Set status to processing in both DBs
        low_db = get_db('low_review_score_db')
        high_db = get_db('high_review_score_db')
        
        update_data = {'status': 'processing'}
        low_db.raw_data_uploads.update_one({'_id': upload_id}, {'$set': update_data})
        high_db.raw_data_uploads.update_one({'_id': upload_id}, {'$set': update_data})
        
        # Process data in chunks
        processor = BulkDataProcessor(chunk_size=1000, max_threads=4)
        result = processor.process_dataframe(df, upload_id)
        
        # Update sales trends in bulk after data is inserted
        update_sales_trend_in_bulk(df)
        
        # Run post-processing hooks
        from post_upload_hooks import post_csv_upload_hook
        post_csv_upload_hook()
        
        # Clean up temp file
        os.remove(temp_file_path)
        
        logger.info(f"Task completed: processed {result['processed_records']} records")
        return result
        
    except Exception as e:
        logger.error(f"Error in background processing task: {str(e)}")
        
        # Update status to failed
        try:
            low_db = get_db('low_review_score_db')
            high_db = get_db('high_review_score_db')
            
            update_data = {
                'status': 'failed',
                'error_message': str(e)
            }
            low_db.raw_data_uploads.update_one({'_id': upload_id}, {'$set': update_data})
            high_db.raw_data_uploads.update_one({'_id': upload_id}, {'$set': update_data})
        except Exception as e2:
            logger.error(f"Error updating upload status: {str(e2)}")
        
        # Attempt to clean up temp file if it exists
        try:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
        except:
            pass
        
        raise

@app.task(bind=True)
def process_analytics_task(self, upload_id):
    """
    Background task for processing analytics after data upload
    
    Args:
        upload_id: ID of upload record
    """
    from mongoengine import connect, get_db
    from django.conf import settings
    
    try:
        # Ensure database connections
        connect(
            db=settings.MONGODB_DATABASES['low_review_score_db']['name'],
            host=settings.MONGODB_DATABASES['low_review_score_db']['uri'],
            alias='low_review_score_db'
        )
        connect(
            db=settings.MONGODB_DATABASES['high_review_score_db']['name'],
            host=settings.MONGODB_DATABASES['high_review_score_db']['uri'],
            alias='high_review_score_db'
        )
        
        # Update predictions and additional analytics
        from core.utils import process_analytics_for_upload
        process_analytics_for_upload(upload_id)
        
        logger.info(f"Analytics processing complete for upload {upload_id}")
        
    except Exception as e:
        logger.error(f"Error in analytics processing task: {str(e)}")
        raise
