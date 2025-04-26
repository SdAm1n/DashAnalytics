from mongoengine import Document, EmbeddedDocument, fields
from django.contrib.auth.models import User
from django.db import models
from datetime import datetime
from django.contrib.auth.hashers import make_password, check_password

# MongoDB Models
class MongoUser(Document):
    username = fields.StringField(required=True, unique=True)
    email = fields.EmailField(required=True, unique=True)
    password = fields.StringField(required=True)
    first_name = fields.StringField()
    last_name = fields.StringField()
    is_active = fields.BooleanField(default=True)
    date_joined = fields.DateTimeField(default=datetime.utcnow)
    last_login = fields.DateTimeField()

    meta = {
        'collection': 'users',
        'indexes': ['username', 'email']
    }

    @property
    def pk(self):
        return str(self.id)

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    @property
    def is_staff(self):
        return False

    def get_username(self):
        return self.username

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    def set_password(self, raw_password):
        self.password = make_password(raw_password)
        self.save(skip_password_hash=True)

    def save(self, *args, **kwargs):
        if not self.date_joined:
            self.date_joined = datetime.utcnow()
        # Hash password if not already hashed
        if self.password and not self.password.startswith('pbkdf2_sha256$') and not kwargs.get('skip_password_hash', False):
            self.password = make_password(self.password)
        if 'skip_password_hash' in kwargs:
            del kwargs['skip_password_hash']
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.username

    def has_perm(self, perm, obj=None):
        return True

    def has_module_perms(self, app_label):
        return True

class Customer(Document):
    customer_id = fields.StringField(required=True, unique=True)
    name = fields.StringField(required=True)
    email = fields.EmailField(required=True, unique=True)
    age = fields.IntField(required=False)
    gender = fields.StringField(choices=('Male', 'Female', 'Other'), required=False)
    location = fields.StringField(required=False)
    registration_date = fields.DateTimeField(default=datetime.utcnow)
    last_purchase_date = fields.DateTimeField(required=False)
    total_purchases = fields.DecimalField(precision=2, required=False)
    preferred_category = fields.StringField(required=False)
    meta = {'collection': 'customers', 'indexes': ['customer_id', 'email']}

class Product(Document):
    product_id = fields.StringField(required=True, unique=True)
    name = fields.StringField(required=True)
    category = fields.StringField(required=True)
    sub_category = fields.StringField(required=False)
    price = fields.DecimalField(precision=2, required=True, min_value=0)
    cost = fields.DecimalField(precision=2, required=False)
    description = fields.StringField(required=False)
    stock_quantity = fields.IntField(default=0)
    rating = fields.FloatField(required=False, min_value=0, max_value=5)
    listing_date = fields.DateTimeField(default=datetime.utcnow)
    meta = {'collection': 'products', 'indexes': ['product_id']}

class OrderItem(EmbeddedDocument):
    product = fields.ReferenceField(Product, required=True)
    quantity = fields.IntField(required=True, min_value=1)
    price = fields.DecimalField(precision=2, required=True, min_value=0)
    discount = fields.DecimalField(precision=2, default=0, min_value=0)

class Order(Document):
    order_id = fields.StringField(required=True, unique=True)
    customer = fields.ReferenceField(Customer, required=True)
    order_date = fields.DateTimeField(required=True)
    items = fields.EmbeddedDocumentListField(OrderItem, required=True)
    total_amount = fields.DecimalField(precision=2, required=True, min_value=0)
    payment_method = fields.StringField(required=True)
    shipping_address = fields.StringField(required=False)
    order_status = fields.StringField(
        choices=('Pending', 'Processing', 'Shipped', 'Delivered', 'Cancelled'),
        default='Delivered'
    )
    delivery_date = fields.DateTimeField(required=False)
    meta = {'collection': 'orders', 'indexes': ['order_id', 'customer']}

class RawDataUpload(Document):
    file_name = fields.StringField(required=True)
    upload_date = fields.DateTimeField(required=True, default=datetime.utcnow)
    file_size = fields.IntField(required=True, min_value=0)
    file_hash = fields.StringField(required=True, unique=True)  # SHA-256 hash of file contents
    row_count = fields.IntField(required=False)
    processed = fields.BooleanField(default=False)
    processed_date = fields.DateTimeField(required=False)
    meta = {'collection': 'raw_data_uploads'}

# User Profile as MongoDB Document
class UserProfile(Document):
    user = fields.ReferenceField(MongoUser, required=True, unique=True)
    theme_preference = fields.StringField(
        choices=['light', 'dark'],
        default='light'
    )
    meta = {'collection': 'user_profiles'}
