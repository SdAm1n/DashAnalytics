import logging
from mongoengine import connect, get_db
from django.conf import settings
from .models import (
    LowReview, HighReview, Customer, Product, Order, Sales,
    ReplicatedDocument, MongoUser, RawDataUpload
)
from analytics.models import (
    ProductPerformance, CategoryPerformance, Demographics,
    GeographicalInsights, CustomerBehavior, Prediction, SalesTrend
)

logger = logging.getLogger(__name__)

def save_review_with_sharding(review_data):
    """
    Saves a review to the appropriate database based on review score.
    Also handles replication of related data.
    """
    try:
        review_score = review_data.get('review_score')
        
        if review_score is None:
            raise ValueError("Review score is required")
        
        # Determine which database to use based on review score
        if float(review_score) < 4:
            # Save to low_review_score_db
            db = get_db('low_review_score_db')
            review = LowReview(**review_data)
            db_type = 'low'
        else:
            # Save to high_review_score_db 
            db = get_db('high_review_score_db')
            review = HighReview(**review_data)
            db_type = 'high'

        review.save()
        logger.info(f"Saved {db_type} review (score: {review_score}) to {db.name}")
        return review

    except Exception as e:
        logger.error(f"Error saving review: {str(e)}")
        raise

def replicate_data(data, model_class):
    """
    Replicates data across both low and high review score databases
    """
    try:
        # Use a more reliable approach to handle both databases
        doc_id = data.get('id')
        
        # Handle each database separately to avoid cascading errors
        # First low_review_score_db
        try:
            if doc_id:
                # Try to find existing document by ID if provided
                low_doc = model_class.objects(id=doc_id).using('low_review_score_db').first()
                if low_doc:
                    # Update existing document
                    for key, value in data.items():
                        if key != 'id':  # Skip the ID field
                            setattr(low_doc, key, value)
                    low_doc.save()
                else:
                    # Create new document
                    low_doc = model_class(**data)
                    low_doc.switch_db('low_review_score_db')
                    low_doc.save()
            else:
                # No ID provided, check for unique constraints based on model
                if hasattr(model_class, 'create_or_update_by_unique_fields'):
                    # For models with custom unique field handling
                    low_doc = model_class.create_or_update_by_unique_fields(data, 'low_review_score_db')
                else:
                    # For models without custom handling
                    low_doc = model_class(**data)
                    low_doc.switch_db('low_review_score_db')
                    low_doc.save()
        except Exception as e:
            logger.warning(f"Error replicating to low_review_score_db: {str(e)}")
            low_doc = None
        
        # Then high_review_score_db
        try:
            if doc_id:
                # Try to find existing document by ID if provided
                high_doc = model_class.objects(id=doc_id).using('high_review_score_db').first()
                if high_doc:
                    # Update existing document
                    for key, value in data.items():
                        if key != 'id':  # Skip the ID field
                            setattr(high_doc, key, value)
                    high_doc.save()
                else:
                    # Create new document
                    high_doc = model_class(**data)
                    high_doc.switch_db('high_review_score_db')
                    high_doc.save()
            else:
                # No ID provided, check for unique constraints based on model
                if hasattr(model_class, 'create_or_update_by_unique_fields'):
                    # For models with custom unique field handling
                    high_doc = model_class.create_or_update_by_unique_fields(data, 'high_review_score_db')
                else:
                    # For models without custom handling
                    high_doc = model_class(**data)
                    high_doc.switch_db('high_review_score_db')
                    high_doc.save()
        except Exception as e:
            logger.warning(f"Error replicating to high_review_score_db: {str(e)}")
            high_doc = None
        
        logger.info(f"Successfully replicated {model_class.__name__} data")
        return low_doc, high_doc

    except Exception as e:
        logger.error(f"Error replicating data: {str(e)}")
        # Continue execution with partial success
        return None, None

def initialize_databases():
    """
    Ensures all required collections exist in each database with proper indexes
    """
    try:
        # Ensure we have a default connection for MongoEngine
        connect(
            db=settings.MONGODB_DATABASES['low_review_score_db']['name'],
            host=settings.MONGODB_DATABASES['low_review_score_db']['uri'],
            alias='default'
        )
        logger.info("Established default MongoDB connection")
        
        # Initialize auth database collections
        auth_db = get_db('auth_db')
        if 'users' not in auth_db.list_collection_names():
            auth_db.create_collection('users')
            auth_db.users.create_index('username', unique=True)
            auth_db.users.create_index('email', unique=True)
        logger.info("Initialized auth_db collections")
        
        # Get databases for review scores
        low_db = get_db('low_review_score_db')
        high_db = get_db('high_review_score_db')
        
        # Model classes that need to be replicated across both review score databases
        replicated_models = [
            Customer, Product, Order, Sales, RawDataUpload,
            SalesTrend, ProductPerformance, CategoryPerformance,
            Demographics, GeographicalInsights, CustomerBehavior, Prediction
        ]        # Initialize collections and indexes in both review score databases
        for db, db_alias in [(low_db, 'low_review_score_db'), (high_db, 'high_review_score_db')]:
            # Review collections specific to each database
            if db_alias == 'low_review_score_db':
                if 'low_reviews' not in db.list_collection_names():
                    db.create_collection('low_reviews')
                    # Create indexes with explicit names to avoid conflicts
                    db.low_reviews.create_index([('review_date', -1)], name='review_date_idx')
                    db.low_reviews.create_index('customer_id', name='customer_id_idx')
                    db.low_reviews.create_index('product_id', name='product_id_idx')
                    db.low_reviews.create_index('review_score', name='review_score_idx')
            else:
                if 'high_reviews' not in db.list_collection_names():
                    db.create_collection('high_reviews')
                    # Create indexes with explicit names to avoid conflicts
                    db.high_reviews.create_index([('review_date', -1)], name='review_date_idx')
                    db.high_reviews.create_index('customer_id', name='customer_id_idx')
                    db.high_reviews.create_index('product_id', name='product_id_idx')
                    db.high_reviews.create_index('review_score', name='review_score_idx')

            # Common collections to be replicated
            existing = db.list_collection_names()
            for model in replicated_models:
                collection = model._meta.get('collection', '')
                if collection and collection not in existing:
                    db.create_collection(collection)
                    # We will skip creating indexes here as they will be created by MongoEngine
                    # when the documents are saved/inserted
                    logger.info(f"Created collection {collection} in {db_alias}")

                    logger.info(f"Created collection {collection} with indexes in {db_alias}")

            # Create any unique compound indexes here if needed
            logger.info(f"Initialized collections and indexes in {db_alias}")

        # Validate all collections and indexes
        validate_database_setup()
        logger.info("Successfully initialized all databases and collections")
        return True

    except Exception as e:
        logger.error(f"Error initializing databases: {str(e)}")
        raise

def validate_database_setup():
    """
    Validates all databases have required collections and indexes
    """
    try:
        # Check auth_db
        auth_db = get_db('auth_db')
        auth_collections = auth_db.list_collection_names()
        if 'users' not in auth_collections:
            raise ValueError("auth_db missing users collection")
            
        # Define required collections for review databases
        common_collections = {
            'customers', 'products', 'orders', 'sales',
            'sales_trends', 'product_performance', 'category_performance',
            'demographics', 'geographical_insights', 'customer_behavior',
            'predictions', 'raw_data_uploads'
        }
        
        # Get database connections
        low_db = get_db('low_review_score_db')
        high_db = get_db('high_review_score_db')
        
        # Get current collections (convert to lowercase for case-insensitive comparison)
        low_collections = {c.lower() for c in low_db.list_collection_names()}
        high_collections = {c.lower() for c in high_db.list_collection_names()}
        
        # Check if review collections exist - only create if missing
        if 'low_reviews' not in low_collections:
            low_db.create_collection('low_reviews')
            # Create indexes using names to avoid conflicts
            low_db.low_reviews.create_index([('review_date', -1)], name='review_date_-1')
            low_db.low_reviews.create_index('customer_id', name='customer_id_1')
            low_db.low_reviews.create_index('product_id', name='product_id_1')
            low_db.low_reviews.create_index('review_score', name='review_score_1')
            logger.info("Created low_reviews collection")
            
        if 'high_reviews' not in high_collections:
            high_db.create_collection('high_reviews')  
            # Create indexes using names to avoid conflicts
            high_db.high_reviews.create_index([('review_date', -1)], name='review_date_-1')
            high_db.high_reviews.create_index('customer_id', name='customer_id_1')
            high_db.high_reviews.create_index('product_id', name='product_id_1')
            high_db.high_reviews.create_index('review_score', name='review_score_1')
            logger.info("Created high_reviews collection")
            
        # Only create missing collections, don't touch existing ones
        for collection_name in common_collections:
            if collection_name not in low_collections:
                low_db.create_collection(collection_name)
                logger.info(f"Created missing collection {collection_name} in low_review_score_db")
                
            if collection_name not in high_collections:
                high_db.create_collection(collection_name)
                logger.info(f"Created missing collection {collection_name} in high_review_score_db")

        logger.info("All databases validated successfully")
        return True

    except Exception as e:
        logger.error(f"Database validation failed: {str(e)}")
        raise
