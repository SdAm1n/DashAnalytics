from mongoengine import Document, EmbeddedDocument, fields
from datetime import datetime
from django.contrib.auth.hashers import make_password, check_password

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
    customer_id = fields.IntField(required=True, primary_key=True)
    gender = fields.StringField(required=True)
    age = fields.IntField(required=True)
    city = fields.StringField(required=True)
    meta = {'collection': 'customers'}

class Product(Document):
    product_id = fields.IntField(required=True, primary_key=True)
    product_name = fields.StringField(required=True)
    category_id = fields.IntField(required=True)
    category_name = fields.StringField(required=True)
    price = fields.FloatField(required=True)
    meta = {'collection': 'products'}

class Order(Document):
    order_id = fields.StringField(primary_key=True)
    order_date = fields.DateTimeField(default=datetime.now)
    customer_id = fields.ReferenceField(Customer, required=True)
    product_id = fields.ReferenceField(Product, required=True)
    quantity = fields.IntField(required=True)
    review_score = fields.FloatField()
    meta = {'collection': 'orders'}

class OrderItem(EmbeddedDocument):
    product = fields.ReferenceField(Product, required=True)
    quantity = fields.IntField(required=True, min_value=1)
    unit_price = fields.DecimalField(precision=2, required=True)

class Sales(Document):
    id = fields.StringField(primary_key=True)
    customer_id = fields.StringField(required=True)
    product_id = fields.StringField(required=True)
    quantity = fields.IntField(required=True)
    sale_date = fields.DateTimeField(required=True)
    revenue = fields.FloatField(required=True)
    profit = fields.FloatField(required=True)
    city = fields.StringField(required=True)
    meta = {'collection': 'sales'}

class RawDataUpload(Document):
    file_name = fields.StringField(required=True)
    upload_date = fields.DateTimeField(default=datetime.utcnow)
    status = fields.StringField(choices=['pending', 'processing', 'completed', 'failed'])
    error_message = fields.StringField()
    processed_records = fields.IntField(default=0)
    meta = {'collection': 'raw_data_uploads'}

class UserProfile(Document):
    user = fields.ReferenceField(MongoUser, required=True, unique=True)
    theme_preference = fields.StringField(choices=['light', 'dark'], default='light')
    meta = {'collection': 'user_profiles'}
