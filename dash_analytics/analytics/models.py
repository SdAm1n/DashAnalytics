from mongoengine import Document, EmbeddedDocument, fields
from datetime import datetime
from core.models import ReplicatedDocument

# We don't need to redefine Sales class here as it's already defined in core.models
# Removing this duplicate class to avoid conflicts

# Review class is not needed here as we use LowReview and HighReview from core.models
# Removing this class to avoid conflicts

class SalesTrend(ReplicatedDocument):
    id = fields.StringField(primary_key=True)
    period_type = fields.StringField(required=True)  # 'weekly', 'monthly', 'yearly', 'seasonal'
    period_value = fields.StringField(required=True)  # e.g. '2023-W01', '2023-01', '2023', 'Spring'
    total_sales = fields.FloatField(required=True)
    sales_growth_rate = fields.FloatField(required=True)
    sales_percentage = fields.FloatField(required=True)
    meta = {
        'collection': 'sales_trends',
        'db_alias': 'low_review_score_db',
        'indexes': [
            {
                'fields': ['period_type', 'period_value'],
                'name': 'period_type_period_value_idx',
                'unique': False
            }
        ]
    }
    
    @classmethod
    def create_or_update_by_unique_fields(cls, data, db_alias):
        """Create or update document based on period_type and period_value"""
        query = {
            'period_type': data.get('period_type'),
            'period_value': data.get('period_value')
        }
        
        # Find existing document
        doc = cls.objects(**query).using(db_alias).first()
        if doc:
            # Update existing document
            for key, value in data.items():
                if key != 'id':  # Skip the ID field
                    setattr(doc, key, value)
            doc.save()
            
            # Also update in the other database to ensure replication
            other_db = 'high_review_score_db' if db_alias == 'low_review_score_db' else 'low_review_score_db'
            other_doc = cls.objects(**query).using(other_db).first()
            
            if other_doc:
                # Update other document with the same data
                for key, value in data.items():
                    if key != 'id':  # Skip the ID field
                        setattr(other_doc, key, value)
                other_doc.save()
            else:
                # Create in other DB if it doesn't exist there
                other_doc = cls(**data)
                if doc.id:
                    other_doc.id = doc.id  # Use the same ID for consistency
                other_doc.switch_db(other_db)
                other_doc.save()
        else:
            # Create new document
            doc = cls(**data)
            doc.switch_db(db_alias)
            doc.save()
            
            # Also create in other DB for immediate replication
            other_db = 'high_review_score_db' if db_alias == 'low_review_score_db' else 'low_review_score_db'
            other_doc = cls(**data)
            if doc.id:
                other_doc.id = doc.id  # Use the same ID for consistency
            other_doc.switch_db(other_db)
            other_doc.save()
        return doc

class ProductPerformance(ReplicatedDocument):
    id = fields.StringField(primary_key=True)
    product_id = fields.StringField(required=True)
    category = fields.StringField(required=True)
    total_quantity_sold = fields.IntField(required=True)
    average_revenue = fields.FloatField(required=True)
    is_best_selling = fields.BooleanField(default=False)
    is_worst_selling = fields.BooleanField(default=False)
    is_highest_profit_category = fields.BooleanField(default=False)
    meta = {
        'collection': 'product_performance',
        'db_alias': 'low_review_score_db',
        'indexes': [
            {'fields': ['product_id'], 'name': 'product_id_idx', 'unique': False},
            {'fields': ['category'], 'name': 'category_idx', 'unique': False},
            {'fields': ['total_quantity_sold'], 'name': 'total_quantity_sold_idx', 'unique': False}
        ]
    }
    
    @classmethod
    def create_or_update_by_unique_fields(cls, data, db_alias):
        """Create or update document based on product_id"""
        query = {'product_id': data.get('product_id')}
        
        # Find existing document
        doc = cls.objects(**query).using(db_alias).first()
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

class CategoryPerformance(ReplicatedDocument):
    id = fields.StringField(primary_key=True)
    category = fields.StringField(required=True)
    total_quantity_sold = fields.IntField(required=True)
    average_revenue = fields.FloatField(required=True)
    highest_profit = fields.BooleanField(default=False)
    meta = {
        'collection': 'category_performance',
        'db_alias': 'low_review_score_db',
        'indexes': [
            {'fields': ['category'], 'name': 'category_idx', 'unique': False},
            {'fields': ['total_quantity_sold'], 'name': 'total_quantity_sold_idx', 'unique': False},
            {'fields': ['average_revenue'], 'name': 'average_revenue_idx', 'unique': False}
        ]
    }
    
    @classmethod
    def create_or_update_by_unique_fields(cls, data, db_alias):
        """Create or update document based on category"""
        query = {'category': data.get('category')}
        
        # Find existing document
        doc = cls.objects(**query).using(db_alias).first()
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

class Demographics(ReplicatedDocument):
    id = fields.StringField(primary_key=True)
    age_group = fields.StringField(required=True)
    gender = fields.StringField(required=True)
    total_customers = fields.IntField(required=True)
    total_spent = fields.FloatField(required=True)
    meta = {
        'collection': 'demographics',
        'db_alias': 'low_review_score_db',
        'indexes': [
            {
                'fields': ['age_group', 'gender'],
                'unique': False,
                'name': 'age_group_gender_idx'
            }
        ]
    }
    
    @classmethod
    def create_or_update_by_unique_fields(cls, data, db_alias):
        """Create or update a document based on age_group and gender"""
        query = {
            'age_group': data.get('age_group'),
            'gender': data.get('gender')
        }
        
        # Find existing document
        doc = cls.objects(**query).using(db_alias).first()
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

class GeographicalInsights(ReplicatedDocument):
    id = fields.StringField(primary_key=True)
    city = fields.StringField(required=True)
    total_sales = fields.FloatField(required=True)
    total_orders = fields.IntField(required=True)
    average_order_value = fields.FloatField(required=True)
    meta = {
        'collection': 'geographical_insights',
        'db_alias': 'low_review_score_db',
        'indexes': [
            {
                'fields': ['city'],
                'unique': False,
                'name': 'city_idx'
            }
        ]
    }
    
    @classmethod
    def create_or_update_by_unique_fields(cls, data, db_alias):
        """Create or update document based on city"""
        query = {'city': data.get('city')}
        
        # Find existing document
        doc = cls.objects(**query).using(db_alias).first()
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

class CustomerBehavior(ReplicatedDocument):
    id = fields.StringField(primary_key=True)
    customer_id = fields.StringField(required=True)
    total_purchases = fields.IntField(required=True)
    total_spent = fields.FloatField(required=True)
    purchase_frequency = fields.FloatField(required=True)
    customer_segment = fields.StringField(required=True)  # 'VIP', 'Regular', 'Occasional'
    meta = {
        'collection': 'customer_behavior',
        'db_alias': 'low_review_score_db',
        'indexes': [
            {'fields': ['customer_id'], 'name': 'customer_id_idx', 'unique': False},
            {'fields': ['total_purchases'], 'name': 'total_purchases_idx', 'unique': False},
            {'fields': ['total_spent'], 'name': 'total_spent_idx', 'unique': False},
            {'fields': ['customer_segment'], 'name': 'customer_segment_idx', 'unique': False},
            {'fields': ['-total_spent'], 'name': 'neg_total_spent_idx', 'unique': False}  # Index for sorting by highest spenders
        ]
    }
    
    @classmethod
    def create_or_update_by_unique_fields(cls, data, db_alias):
        """Create or update document based on customer_id"""
        query = {'customer_id': data.get('customer_id')}
        
        # Find existing document
        doc = cls.objects(**query).using(db_alias).first()
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

class Prediction(ReplicatedDocument):
    id = fields.StringField(primary_key=True)
    prediction_type = fields.StringField(required=True)  # 'future_sales_trend', 'future_top_product', 'correlation'
    prediction_period = fields.StringField(required=True)  # e.g. '2024-Q1'
    predicted_value = fields.StringField(required=True)
    details = fields.StringField()
    meta = {
        'collection': 'predictions',
        'db_alias': 'low_review_score_db',
        'indexes': [
            {'fields': ['prediction_type', 'prediction_period'], 'name': 'pred_type_period_idx', 'unique': False},
            {'fields': ['prediction_period'], 'name': 'prediction_period_idx', 'unique': False}
        ]
    }
    
    @classmethod
    def create_or_update_by_unique_fields(cls, data, db_alias):
        """Create or update document based on prediction_type and prediction_period"""
        query = {
            'prediction_type': data.get('prediction_type'),
            'prediction_period': data.get('prediction_period')
        }
        
        # Find existing document
        doc = cls.objects(**query).using(db_alias).first()
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
