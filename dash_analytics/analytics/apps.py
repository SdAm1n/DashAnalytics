from django.apps import AppConfig
from django.db.models.signals import post_migrate

class AnalyticsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'analytics'

    def ready(self):
        from mongoengine import get_connection, get_db
        from django.conf import settings
        from . import models

        # Get existing connection instead of creating a new one
        connection = get_connection()
        db = get_db()

        # Initialize all collections
        model_classes = [
            models.Sales,
            models.Review,
            models.SalesTrend,
            models.ProductPerformance,
            models.CategoryPerformance,
            models.Demographics,
            models.GeographicalInsights,
            models.CustomerBehavior,
            models.Prediction,
            
        ]

        # Create collections if they don't exist
        existing_collections = db.list_collection_names()
        for model_class in model_classes:
            collection_name = model_class._meta['collection']
            if collection_name not in existing_collections:
                db.create_collection(collection_name)
