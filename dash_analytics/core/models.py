from mongoengine import Document, EmbeddedDocument, fields, connect
from datetime import datetime
from django.contrib.auth.hashers import make_password, check_password
from django.conf import settings

# Database connections are managed in settings.py

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
        'indexes': ['username', 'email'],
        'db_alias': 'auth_db'  # This ensures users are only stored in auth_db
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

class LowReview(Document):
    id = fields.StringField(primary_key=True)
    product_id = fields.StringField(required=True)
    customer_id = fields.StringField(required=True)
    review_score = fields.FloatField(required=True)  # Changed to FloatField to match actual data
    sentiment = fields.StringField()
    review_text = fields.StringField()
    review_date = fields.DateTimeField(default=datetime.utcnow)

    meta = {
        'collection': 'low_reviews',
        'indexes': [
            {'fields': ['product_id'], 'name': 'product_id_low_reviews_idx'},
            {'fields': ['customer_id'], 'name': 'customer_id_low_reviews_idx'},
            {'fields': ['review_score'], 'name': 'review_score_low_reviews_idx'}
        ],
        'db_alias': 'low_review_score_db'
    }

class HighReview(Document):
    id = fields.StringField(primary_key=True)
    product_id = fields.StringField(required=True)
    customer_id = fields.StringField(required=True)
    review_score = fields.FloatField(required=True)  # Changed to FloatField to match actual data
    sentiment = fields.StringField()
    review_text = fields.StringField()
    review_date = fields.DateTimeField(default=datetime.utcnow)

    meta = {
        'collection': 'high_reviews',
        'indexes': [
            {'fields': ['product_id'], 'name': 'product_id_high_reviews_idx'},
            {'fields': ['customer_id'], 'name': 'customer_id_high_reviews_idx'},
            {'fields': ['review_score'], 'name': 'review_score_high_reviews_idx'}
        ],
        'db_alias': 'high_review_score_db'
    }

# Base classes for replicated collections
class ReplicatedDocument(Document):
    meta = {
        'abstract': True,
        'auto_create_index': True,
    }
    
    @classmethod
    def save_to_all(cls, data):
        """Save the same data to both databases"""
        from core.utils import replicate_data
        return replicate_data(data, cls)
    
    @classmethod
    def create_or_update_by_unique_fields(cls, data, db_alias):
        """Create or update a document based on its unique fields"""
        # This method should be overridden by subclasses with unique fields
        doc = cls(**data)
        doc.switch_db(db_alias)
        doc.save()
        return doc

class Customer(ReplicatedDocument):
    customer_id = fields.IntField(required=True, unique=True)
    gender = fields.StringField(required=True)
    age = fields.IntField(required=True)
    city = fields.StringField(required=True)
    meta = {
        'collection': 'customers',
        'indexes': [
            {'fields': ['customer_id'], 'unique': True, 'name': 'customer_id_unique_idx'}
        ],
        'db_alias': 'low_review_score_db'
    }

    @classmethod
    def create_or_update_by_unique_fields(cls, data, db_alias):
        """Create or update a document based on customer_id"""
        try:
            # Make sure data types are correct
            cleaned_data = data.copy()
            # Handle customer_id - ensure it's an integer
            customer_id = data.get('customer_id')
            if not customer_id:
                raise ValueError("customer_id is required")
            
            # Convert to integer if it's not already
            if not isinstance(customer_id, int):
                try:
                    cleaned_data['customer_id'] = int(customer_id)
                except (ValueError, TypeError):
                    raise ValueError(f"customer_id must be convertible to integer: {customer_id}")
            
            # Handle gender - ensure it's a string
            if 'gender' in data:
                cleaned_data['gender'] = str(data['gender'])
            
            # Handle age - ensure it's an integer
            if 'age' in data:
                if not isinstance(data['age'], int):
                    try:
                        cleaned_data['age'] = int(data['age'])
                    except (ValueError, TypeError):
                        raise ValueError(f"age must be convertible to integer: {data['age']}")
            
            # Handle city - ensure it's a string
            if 'city' in data:
                cleaned_data['city'] = str(data['city'])
                
            # Find existing document
            doc = cls.objects(customer_id=cleaned_data['customer_id']).using(db_alias).first()
            if doc:
                # Update existing document
                for key, value in cleaned_data.items():
                    if key != 'id':  # Skip the ID field
                        setattr(doc, key, value)
                doc.save()
            else:
                # Create new document
                doc = cls(**cleaned_data)
                doc.switch_db(db_alias)
                doc.save()
            return doc
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error in create_or_update_by_unique_fields for Customer: {str(e)}")
            raise

class Product(ReplicatedDocument):
    product_id = fields.IntField(required=True, unique=True)
    category_id = fields.IntField(required=True)
    category_name = fields.StringField(required=True)
    product_name = fields.StringField(required=True)
    price = fields.FloatField(required=True)
    meta = {
        'collection': 'products',
        'indexes': [
            {'fields': ['product_id'], 'unique': True, 'name': 'product_id_unique_idx'}
        ],
        'db_alias': 'low_review_score_db'
    }
    
    @classmethod
    def create_or_update_by_unique_fields(cls, data, db_alias):
        """Create or update a document based on product_id"""
        try:
            product_id = data.get('product_id')
            if not product_id:
                raise ValueError("product_id is required")
                
            # Find existing document
            doc = cls.objects(product_id=product_id).using(db_alias).first()
            if doc:
                # Update existing document
                for key, value in data.items():
                    if key != 'id':  # Skip the ID field
                        setattr(doc, key, value)
                doc.save()
            else:
                # Create new document
                doc = cls(**data)
                doc.switch_db(db_alias)
                doc.save()
            return doc
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error in create_or_update_by_unique_fields for Product: {str(e)}")
            raise

class Order(ReplicatedDocument):
    order_id = fields.StringField(required=True, unique=True)
    order_date = fields.DateTimeField(default=datetime.utcnow)
    quantity = fields.IntField(required=True)
    payment_method = fields.StringField()
    review_score = fields.FloatField()  # Added for temporary storage during analysis
    customer_id = fields.ReferenceField(Customer, required=True)
    product_id = fields.ReferenceField(Product, required=True)
    meta = {
        'collection': 'orders',
        'indexes': [
            {'fields': ['order_id'], 'unique': True, 'name': 'order_id_unique_idx'},
            {'fields': ['customer_id'], 'name': 'customer_id_idx'},
            {'fields': ['product_id'], 'name': 'product_id_idx'}
        ],
        'db_alias': 'low_review_score_db'
    }
    
    @classmethod
    def create_or_update_by_unique_fields(cls, data, db_alias):
        """Create or update a document based on order_id"""
        try:
            order_id = data.get('order_id')
            if not order_id:
                raise ValueError("order_id is required")
                
            # Find existing document
            doc = cls.objects(order_id=order_id).using(db_alias).first()
            if doc:
                # Update existing document
                for key, value in data.items():
                    if key != 'id':  # Skip the ID field
                        setattr(doc, key, value)
                doc.save()
            else:
                # Create new document
                doc = cls(**data)
                doc.switch_db(db_alias)
                doc.save()
            return doc
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error in create_or_update_by_unique_fields for Order: {str(e)}")
            raise

# Demographics and GeographicalInsights models moved to analytics/models.py

class Sales(ReplicatedDocument):
    id = fields.StringField(primary_key=True)
    customer_id = fields.StringField(required=True)
    product_id = fields.StringField(required=True)
    quantity = fields.IntField(required=True)
    sale_date = fields.DateTimeField(required=True)
    revenue = fields.FloatField(required=True)
    profit = fields.FloatField(required=True)
    city = fields.StringField(required=True)
    meta = {
        'collection': 'sales',
        'indexes': [
            {'fields': ['customer_id'], 'name': 'customer_id_idx'},
            {'fields': ['product_id'], 'name': 'product_id_idx'},
            {'fields': [('sale_date', -1)], 'name': 'sale_date_idx'}
        ],
        'db_alias': 'low_review_score_db'
    }
    
    @classmethod
    def create_or_update_by_unique_fields(cls, data, db_alias):
        """Create or update a document based on ID"""
        try:
            doc_id = data.get('id')
            if not doc_id:
                raise ValueError("id is required")
                
            # Find existing document
            doc = cls.objects(id=doc_id).using(db_alias).first()
            if doc:
                # Update existing document
                for key, value in data.items():
                    if key != 'id':  # Skip the ID field
                        setattr(doc, key, value)
                doc.save()
            else:
                # Create new document
                doc = cls(**data)
                doc.switch_db(db_alias)
                doc.save()
            return doc
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error in create_or_update_by_unique_fields for Sales: {str(e)}")
            raise

class RawDataUpload(ReplicatedDocument):
    file_name = fields.StringField(required=True)
    upload_date = fields.DateTimeField(default=datetime.utcnow)
    status = fields.StringField(choices=['pending', 'processing', 'completed', 'failed'], default='pending')
    error_message = fields.StringField()
    processed_records = fields.IntField(default=0)
    total_records = fields.IntField(default=0)
    low_reviews_count = fields.IntField(default=0)
    high_reviews_count = fields.IntField(default=0)
    processing_time = fields.FloatField(default=0.0)
    meta = {
        'collection': 'raw_data_uploads',
        'indexes': ['file_name', 'upload_date'],
        'db_alias': 'low_review_score_db'
    }
