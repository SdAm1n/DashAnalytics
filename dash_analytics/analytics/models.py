from mongoengine import Document, EmbeddedDocument, fields
import datetime


class Prediction(Document):
    prediction_id = fields.StringField(required=True, unique=True)
    prediction_type = fields.StringField(required=True, choices=(
        'sales_trend', 'product_performance', 'customer_behavior'))
    creation_date = fields.DateTimeField(default=datetime.datetime.now)
    prediction_data = fields.DictField()
    period_start = fields.DateTimeField()
    period_end = fields.DateTimeField()
    accuracy = fields.FloatField()
    meta = {'collection': 'predictions'}


class Analysis(Document):
    analysis_id = fields.StringField(required=True, unique=True)
    analysis_type = fields.StringField(required=True, choices=(
        'sales_trend', 'product_performance', 'customer_demographics',
        'geographical_insights', 'customer_behavior'
    ))
    creation_date = fields.DateTimeField(default=datetime.datetime.now)
    analysis_data = fields.DictField()
    period_start = fields.DateTimeField()
    period_end = fields.DateTimeField()
    meta = {'collection': 'analyses'}


class ProductCorrelation(Document):
    product_a_id = fields.StringField(required=True)
    product_b_id = fields.StringField(required=True)
    correlation_score = fields.FloatField(required=True)
    analysis_date = fields.DateTimeField(default=datetime.datetime.now)
    meta = {'collection': 'product_correlations'}


class CustomerSegment(Document):
    segment_id = fields.StringField(required=True, unique=True)
    segment_name = fields.StringField(required=True)
    criteria = fields.DictField()
    customer_count = fields.IntField(default=0)
    average_purchase_value = fields.DecimalField(precision=2)
    creation_date = fields.DateTimeField(default=datetime.datetime.now)
    meta = {'collection': 'customer_segments'}
