from django.apps import AppConfig
from django.db.models.signals import post_migrate

class AnalyticsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'analytics'

    def ready(self):
        import logging
        from mongoengine import connect, get_db
        from django.conf import settings

        logger = logging.getLogger(__name__)
        
        try:
            # Make sure we have a default connection
            connect(
                db=settings.MONGODB_DATABASES['low_review_score_db']['name'],
                host=settings.MONGODB_DATABASES['low_review_score_db']['uri'],
                alias='default'
            )
            logger.info("Created default connection for analytics app")
            
        except Exception as e:
            logger.error(f"Error setting up default connection: {str(e)}")
            # Don't raise, as this would prevent the app from loading
        
        # Note: Collection initialization is now handled in core.utils.initialize_databases
