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
    segment_type = fields.StringField(required=True)  # 'age_group' or 'gender'
    segment_value = fields.StringField(required=True)  # actual age group or gender value
    total_orders = fields.IntField(required=True)
    average_order_value = fields.FloatField(required=True)
    meta = {'collection': 'demographics'}

class GeographicalInsights(Document):
    id = fields.StringField(primary_key=True)
    city = fields.StringField(required=True)
    total_revenue = fields.FloatField(required=True)
    total_orders = fields.IntField(required=True)
    market_share = fields.FloatField(required=True)
    meta = {'collection': 'geographical_insights'}

class CustomerBehavior(Document):
    id = fields.StringField(primary_key=True)
    customer = fields.ReferenceField('Customer', required=True)
    total_orders = fields.IntField(required=True)
    total_spent = fields.FloatField(required=True)
    average_order_value = fields.FloatField(required=True)
    first_purchase_date = fields.DateTimeField(required=True)
    last_purchase_date = fields.DateTimeField(required=True)
    average_review_score = fields.FloatField(required=True)
    meta = {'collection': 'customer_behavior'}

class Prediction(Document):
    id = fields.StringField(primary_key=True)
    prediction_type = fields.StringField(required=True)  # 'future_sales_trend', 'future_top_product', 'correlation'
    prediction_period = fields.StringField(required=True)  # e.g. '2024-Q1'
    predicted_value = fields.StringField(required=True)
    details = fields.StringField()
    meta = {'collection': 'predictions'}
