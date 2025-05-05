from django.core.management.base import BaseCommand
from core.models import Customer, Product, Order
from analytics.models import (
    Sales, Review, SalesTrend, ProductPerformance, CategoryPerformance,
    Demographics, GeographicalInsights, CustomerBehavior, Prediction
)
from mongoengine import fields
from datetime import datetime
from decimal import Decimal

class Command(BaseCommand):
    help = 'Initialize MongoDB collections for the application'

    def handle(self, *args, **kwargs):
        self.stdout.write('Starting collection initialization...')
        
        try:
            # Initialize core collections
            self._touch_collection(Customer)
            self._touch_collection(Product)
            self._touch_collection(Order)
            self._touch_collection(Sales)
            self._touch_collection(Review)

            # Initialize analytics collections
            self._touch_collection(SalesTrend)
            self._touch_collection(ProductPerformance)
            self._touch_collection(CategoryPerformance)
            self._touch_collection(Demographics)
            self._touch_collection(GeographicalInsights)
            self._touch_collection(CustomerBehavior)
            self._touch_collection(Prediction)
            
            self.stdout.write(self.style.SUCCESS('Successfully initialized collections'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error initializing collections: {str(e)}'))

    def _touch_collection(self, model_class):
        """Helper method to ensure a collection exists by accessing it"""
        try:
            model_class.objects().first()
            self.stdout.write(f'Initialized collection: {model_class._meta["collection"]}')
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Error touching collection {model_class._meta["collection"]}: {str(e)}'))