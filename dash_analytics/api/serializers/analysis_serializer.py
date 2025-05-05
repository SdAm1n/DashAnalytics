from rest_framework import serializers
from analytics.models import SalesTrend
from core.models import Order, Customer, Product


class SalesTrendSerializer(serializers.Serializer):
    period = serializers.CharField()
    total_sales = serializers.DecimalField(max_digits=12, decimal_places=2)
    order_count = serializers.IntegerField()
    growth_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    category_sales = serializers.DictField(required=False)
    region_sales = serializers.DictField(required=False)


class GeographicalInsightSerializer(serializers.Serializer):
    region = serializers.CharField()
    total_sales = serializers.DecimalField(max_digits=12, decimal_places=2)
    customer_count = serializers.IntegerField()
    average_order_value = serializers.DecimalField(max_digits=10, decimal_places=2)
    growth_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    market_share = serializers.DecimalField(max_digits=5, decimal_places=2)


class CustomerAnalyticsSerializer(serializers.Serializer):
    age_group = serializers.CharField()
    gender = serializers.CharField()
    total_customers = serializers.IntegerField()
    total_sales = serializers.DecimalField(max_digits=12, decimal_places=2)
    average_order_value = serializers.DecimalField(max_digits=10, decimal_places=2)
    purchase_frequency = serializers.FloatField()
