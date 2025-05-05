from rest_framework import serializers
from analytics.models import Prediction

class PredictionSerializer(serializers.Serializer):
    id = serializers.CharField(source='id')
    prediction_type = serializers.CharField()
    prediction_period = serializers.CharField()
    predicted_value = serializers.CharField()
    details = serializers.CharField(allow_null=True)
    
    def create(self, validated_data):
        return Prediction.objects.create(**validated_data)

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
