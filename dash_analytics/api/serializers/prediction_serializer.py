from rest_framework import serializers
from analytics.models import Prediction, ProductCorrelation


class PredictionSerializer(serializers.Serializer):
    id = serializers.CharField(source='id')
    prediction_id = serializers.CharField()
    prediction_type = serializers.CharField()
    creation_date = serializers.DateTimeField()
    prediction_data = serializers.DictField()
    period_start = serializers.DateTimeField(required=False, allow_null=True)
    period_end = serializers.DateTimeField(required=False, allow_null=True)
    accuracy = serializers.FloatField(required=False, allow_null=True)

    def create(self, validated_data):
        return Prediction.objects.create(**validated_data)

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class ProductCorrelationSerializer(serializers.Serializer):
    id = serializers.CharField(source='id')
    product_a_id = serializers.CharField()
    product_b_id = serializers.CharField()
    correlation_score = serializers.FloatField()
    analysis_date = serializers.DateTimeField()

    def create(self, validated_data):
        return ProductCorrelation.objects.create(**validated_data)

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
