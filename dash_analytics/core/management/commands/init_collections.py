from django.core.management.base import BaseCommand
from core.models import Customer, Product, Order
from analytics.models import (
    Analysis, Prediction, ProductCorrelation, CustomerSegment,
    Sales, Review, SalesTrend, ProductPerformance, CategoryPerformance,
    Demographics, GeographicalInsights, CustomerBehavior
)
from mongoengine import fields
from datetime import datetime
from decimal import Decimal

class Command(BaseCommand):
    help = 'Initialize MongoDB collections with empty documents'

    def handle(self, *args, **kwargs):
        collections = [
            Customer, Product, Order,  # Core models
            Analysis, Prediction, ProductCorrelation, CustomerSegment,  # Analytics models
            Sales, Review, SalesTrend, ProductPerformance,
            CategoryPerformance, Demographics, GeographicalInsights,
            CustomerBehavior
        ]

        for collection in collections:
            try:
                # Create a dummy document to initialize the collection
                dummy = collection()
                for field in collection._fields:
                    if collection._fields[field].required:
                        if isinstance(collection._fields[field], (fields.StringField, fields.URLField)):
                            if field == 'analysis_type':
                                setattr(dummy, field, 'sales_trend')
                            else:
                                setattr(dummy, field, "dummy")
                        elif isinstance(collection._fields[field], fields.IntField):
                            setattr(dummy, field, 0)
                        elif isinstance(collection._fields[field], fields.FloatField):
                            setattr(dummy, field, 0.0)
                        elif isinstance(collection._fields[field], fields.DateTimeField):
                            setattr(dummy, field, datetime.now())
                        elif isinstance(collection._fields[field], fields.DictField):
                            setattr(dummy, field, {'dummy': 'data'})
                        elif isinstance(collection._fields[field], fields.DecimalField):
                            setattr(dummy, field, Decimal('0.00'))
                        elif isinstance(collection._fields[field], fields.ReferenceField):
                            # Handle reference fields for Order model
                            if field == 'customer_id':
                                customer = Customer(customer_id=0, gender='M', age=0, city='dummy')
                                customer.save()
                                setattr(dummy, field, customer)
                            elif field == 'product_id':
                                product = Product(product_id=0, product_name='dummy', category_id=0, 
                                               category_name='dummy', price=0.0)
                                product.save()
                                setattr(dummy, field, product)

                # Save and delete the dummy document without background indexing
                dummy.save()
                dummy.delete()

                # Clean up any temporary documents we created for references
                if collection == Order:
                    Customer.objects(customer_id=0).delete()
                    Product.objects(product_id=0).delete()

                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully initialized collection for {collection.__name__}'
                    )
                )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'Failed to initialize {collection.__name__}: {str(e)}'
                    )
                )