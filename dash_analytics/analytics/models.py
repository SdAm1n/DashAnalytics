from mongoengine import Document, EmbeddedDocument, fields
from datetime import datetime

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

class Review(Document):
    id = fields.StringField(primary_key=True)
    customer_id = fields.StringField(required=True)
    product_id = fields.StringField(required=True)
    review_score = fields.FloatField(required=True)
    sentiment = fields.StringField(required=True)
    meta = {'collection': 'reviews'}

class SalesTrend(Document):
    id = fields.StringField(primary_key=True)
    period_type = fields.StringField(required=True)  # 'weekly', 'monthly', 'yearly', 'seasonal'
    period_value = fields.StringField(required=True)  # e.g. '2023-W01', '2023-01', '2023', 'Spring'
    total_sales = fields.FloatField(required=True)
    sales_growth_rate = fields.FloatField(required=True)
    sales_percentage = fields.FloatField(required=True)
    meta = {'collection': 'sales_trends'}

class ProductPerformance(Document):
    id = fields.StringField(primary_key=True)
    product_id = fields.StringField(required=True)
    category = fields.StringField(required=True)
    total_quantity_sold = fields.IntField(required=True)
    average_revenue = fields.FloatField(required=True)
    is_best_selling = fields.BooleanField(default=False)
    is_worst_selling = fields.BooleanField(default=False)
    is_highest_profit_category = fields.BooleanField(default=False)
    meta = {'collection': 'product_performance'}

class CategoryPerformance(Document):
    id = fields.StringField(primary_key=True)
    category = fields.StringField(required=True)
    total_quantity_sold = fields.IntField(required=True)
    average_revenue = fields.FloatField(required=True)
    highest_profit = fields.BooleanField(default=False)
    meta = {'collection': 'category_performance'}

class Demographics(Document):
    id = fields.StringField(primary_key=True)
    age_group = fields.StringField(required=True)
    gender = fields.StringField(required=True)
    customer_count = fields.IntField(required=True)
    total_sales = fields.FloatField(required=True)
    meta = {'collection': 'demographics'}

class GeographicalInsights(Document):
    id = fields.StringField(primary_key=True)
    city = fields.StringField(required=True)
    customer_count = fields.IntField(required=True)
    total_sales = fields.FloatField(required=True)
    total_profit = fields.FloatField(required=True)
    total_loss = fields.FloatField(required=True)
    is_highest_customers = fields.BooleanField(default=False)
    is_lowest_customers = fields.BooleanField(default=False)
    is_highest_profit = fields.BooleanField(default=False)
    is_highest_loss = fields.BooleanField(default=False)
    meta = {'collection': 'geographical_insights'}

class CustomerBehavior(Document):
    id = fields.StringField(primary_key=True)
    customer_id = fields.StringField(required=True)
    items_bought_together = fields.StringField(required=True)
    average_review_score = fields.FloatField(required=True)
    sentiment = fields.StringField(required=True)
    meta = {'collection': 'customer_behavior'}

class Prediction(Document):
    id = fields.StringField(primary_key=True)
    prediction_type = fields.StringField(required=True)  # 'future_sales_trend', 'future_top_product', 'correlation'
    prediction_period = fields.StringField(required=True)  # e.g. '2024-Q1'
    predicted_value = fields.StringField(required=True)
    details = fields.StringField()
    meta = {'collection': 'predictions'}

class Analysis(Document):
    id = fields.StringField(primary_key=True)
    analysis_type = fields.StringField(required=True, choices=(
        'sales_trend', 'product_performance', 'customer_demographics',
        'geographical_insights', 'customer_behavior'
    ))
    creation_date = fields.DateTimeField(default=datetime.utcnow)
    analysis_data = fields.DictField(required=True)
    period_start = fields.DateTimeField()
    period_end = fields.DateTimeField()
    meta = {'collection': 'analyses'}

class ProductCorrelation(Document):
    id = fields.StringField(primary_key=True)
    product_a_id = fields.StringField(required=True)
    product_b_id = fields.StringField(required=True)
    correlation_score = fields.FloatField(required=True)
    analysis_date = fields.DateTimeField(default=datetime.utcnow)
    meta = {'collection': 'product_correlations'}

class CustomerSegment(Document):
    id = fields.StringField(primary_key=True)
    segment_id = fields.StringField(required=True, unique=True)
    segment_name = fields.StringField(required=True)
    criteria = fields.DictField(required=True)
    customer_count = fields.IntField(default=0)
    average_purchase_value = fields.DecimalField(precision=2, required=True)
    creation_date = fields.DateTimeField(default=datetime.utcnow)
    meta = {'collection': 'customer_segments'}
