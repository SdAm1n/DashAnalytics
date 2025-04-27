from rest_framework import serializers
from analytics.models import Analysis, CustomerSegment
from core.models import Order, Customer, Product


class AnalysisSerializer(serializers.Serializer):
    id = serializers.CharField(source='id')
    analysis_id = serializers.CharField()
    analysis_type = serializers.CharField()
    creation_date = serializers.DateTimeField()
    analysis_data = serializers.DictField()
    period_start = serializers.DateTimeField(required=False, allow_null=True)
    period_end = serializers.DateTimeField(required=False, allow_null=True)

    def create(self, validated_data):
        return Analysis.objects.create(**validated_data)

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class CustomerSegmentSerializer(serializers.Serializer):
    id = serializers.CharField(source='id')
    segment_id = serializers.CharField()
    segment_name = serializers.CharField()
    criteria = serializers.DictField()
    customer_count = serializers.IntegerField()
    average_purchase_value = serializers.DecimalField(
        max_digits=10, decimal_places=2)
    creation_date = serializers.DateTimeField()

    def create(self, validated_data):
        return CustomerSegment.objects.create(**validated_data)

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


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
