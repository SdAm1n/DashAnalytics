"""
Database Maintenance Utility

This script provides maintenance operations for the DashAnalytics MongoDB databases:
1. Cleans up old log files
2. Optimizes database collections
3. Removes temporary data

Usage:
    python db_maintenance.py [--clean-logs] [--optimize-db] [--clean-temp]
"""

import os
import sys
import time
import argparse
import logging
import shutil
from datetime import datetime, timedelta

# Configure logging
log_filename = f"maintenance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_filename)
    ]
)
logger = logging.getLogger(__name__)

def clean_old_logs(days=7):
    """Remove log files older than specified days"""
    logger.info(f"Cleaning up log files older than {days} days...")
    
    count = 0
    current_dir = os.path.dirname(os.path.abspath(__file__))
    cutoff_date = datetime.now() - timedelta(days=days)
    
    for filename in os.listdir(current_dir):
        if filename.endswith(".log"):
            file_path = os.path.join(current_dir, filename)
            file_modified = datetime.fromtimestamp(os.path.getmtime(file_path))
            
            if file_modified < cutoff_date:
                try:
                    os.remove(file_path)
                    logger.info(f"Removed old log file: {filename}")
                    count += 1
                except Exception as e:
                    logger.error(f"Error removing {filename}: {str(e)}")
    
    logger.info(f"Removed {count} old log files")
    return count

def optimize_database():
    """Optimize MongoDB collections"""
    logger.info("Optimizing database collections...")
    
    try:
        import django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dash_analytics.settings')
        django.setup()
        
        from mongoengine.connection import get_db
        
        databases = ['high_review_score_db', 'low_review_score_db']
        collections_optimized = 0
        
        for db_name in databases:
            db = get_db(db_name)
            
            logger.info(f"Optimizing database: {db_name}")
            collections = db.list_collection_names()
            
            for collection_name in collections:
                logger.info(f"  - Optimizing collection: {collection_name}")
                
                # Run explain to force index usage analysis
                try:
                    db.command('explain', {
                        'aggregate': collection_name,
                        'pipeline': [{'$match': {}}],
                        'cursor': {}
                    }, verbosity='queryPlanner')
                    
                    # Run compact command to optimize storage
                    db.command('compact', collection_name)
                    collections_optimized += 1
                    
                except Exception as e:
                    logger.warning(f"  - Error optimizing {collection_name}: {str(e)}")
        
        logger.info(f"Optimized {collections_optimized} collections")
        return collections_optimized
        
    except Exception as e:
        logger.error(f"Error optimizing database: {str(e)}")
        return 0

def clean_temp_data():
    """Clean temporary data files"""
    logger.info("Cleaning temporary data...")
    
    count = 0
    current_dir = os.path.dirname(os.path.abspath(__file__))
    temp_dirs = ['__pycache__', '.pytest_cache']
    
    # Clean temp directories
    for temp_dir in temp_dirs:
        for root, dirs, files in os.walk(current_dir):
            if temp_dir in dirs:
                temp_path = os.path.join(root, temp_dir)
                try:
                    shutil.rmtree(temp_path)
                    logger.info(f"Removed temp directory: {temp_path}")
                    count += 1
                except Exception as e:
                    logger.error(f"Error removing {temp_path}: {str(e)}")
    
    # Clean .pyc files
    for root, dirs, files in os.walk(current_dir):
        for file in files:
            if file.endswith('.pyc'):
                file_path = os.path.join(root, file)
                try:
                    os.remove(file_path)
                    count += 1
                except Exception as e:
                    logger.error(f"Error removing {file_path}: {str(e)}")
    
    logger.info(f"Cleaned {count} temporary files/directories")
    return count

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Database maintenance utility")
    parser.add_argument('--clean-logs', action='store_true', help='Clean up old log files')
    parser.add_argument('--log-days', type=int, default=7, help='Age of logs to clean (in days)')
    parser.add_argument('--optimize-db', action='store_true', help='Optimize database collections')
    parser.add_argument('--clean-temp', action='store_true', help='Clean temporary data')
    parser.add_argument('--all', action='store_true', help='Perform all maintenance operations')
    
    args = parser.parse_args()
    
    start_time = time.time()
    logger.info("Starting database maintenance...")
    
    # If no arguments or --all is specified, do everything
    do_all = args.all or not (args.clean_logs or args.optimize_db or args.clean_temp)
    
    if args.clean_logs or do_all:
        clean_old_logs(days=args.log_days)
    
    if args.optimize_db or do_all:
        optimize_database()
    
    if args.clean_temp or do_all:
        clean_temp_data()
    
    end_time = time.time()
    duration = end_time - start_time
    logger.info(f"Maintenance completed in {duration:.2f} seconds")
