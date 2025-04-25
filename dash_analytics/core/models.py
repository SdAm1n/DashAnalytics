from mongoengine import Document, EmbeddedDocument, fields
from django.contrib.auth.models import User
from django.db import models

# MongoDB Models


class Customer(Document):
    customer_id = fields.StringField(required=True, unique=True)
    name = fields.StringField(required=True)
    email = fields.EmailField(required=True, unique=True)
    age = fields.IntField()
    gender = fields.StringField(choices=('Male', 'Female', 'Other'))
    location = fields.StringField()
    registration_date = fields.DateTimeField()
    last_purchase_date = fields.DateTimeField()
    total_purchases = fields.DecimalField(precision=2)
    preferred_category = fields.StringField()
    meta = {'collection': 'customers'}


class Product(Document):
    product_id = fields.StringField(required=True, unique=True)
    name = fields.StringField(required=True)
    category = fields.StringField(required=True)
    sub_category = fields.StringField()
    price = fields.DecimalField(precision=2, required=True)
    cost = fields.DecimalField(precision=2)
    description = fields.StringField()
    stock_quantity = fields.IntField(default=0)
    rating = fields.FloatField()
    listing_date = fields.DateTimeField()
    meta = {'collection': 'products'}


class OrderItem(EmbeddedDocument):
    product = fields.ReferenceField(Product)
    quantity = fields.IntField(required=True, min_value=1)
    price = fields.DecimalField(precision=2, required=True)
    discount = fields.DecimalField(precision=2, default=0)


class Order(Document):
    order_id = fields.StringField(required=True, unique=True)
    customer = fields.ReferenceField(Customer)
    order_date = fields.DateTimeField(required=True)
    items = fields.EmbeddedDocumentListField(OrderItem)
    total_amount = fields.DecimalField(precision=2)
    payment_method = fields.StringField()
    shipping_address = fields.StringField()
    order_status = fields.StringField(
        choices=('Pending', 'Processing', 'Shipped', 'Delivered', 'Cancelled'))
    delivery_date = fields.DateTimeField()
    meta = {'collection': 'orders'}


class RawDataUpload(Document):
    file_name = fields.StringField(required=True)
    upload_date = fields.DateTimeField(required=True)
    file_size = fields.IntField()
    row_count = fields.IntField()
    processed = fields.BooleanField(default=False)
    processed_date = fields.DateTimeField()
    meta = {'collection': 'raw_data_uploads'}

# Django Models for user management


class UserProfile(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='profile')
    theme_preference = models.CharField(max_length=10, choices=[(
        'light', 'Light'), ('dark', 'Dark')], default='light')

    def __str__(self):
        return f"{self.user.username}'s profile"
