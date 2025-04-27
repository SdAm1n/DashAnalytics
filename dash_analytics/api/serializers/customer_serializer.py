from rest_framework import serializers
from core.models import Customer


class CustomerSerializer(serializers.Serializer):
    id = serializers.CharField(source='id')
    customer_id = serializers.CharField()
    email = serializers.EmailField()
    age = serializers.IntegerField(required=False, allow_null=True)
    gender = serializers.CharField(required=False, allow_null=True)
    location = serializers.CharField(required=False, allow_null=True)
    registration_date = serializers.DateTimeField(
        required=False, allow_null=True)
    last_purchase_date = serializers.DateTimeField(
        required=False, allow_null=True)
    total_purchases = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True)
    preferred_category = serializers.CharField(required=False, allow_null=True)

    def create(self, validated_data):
        return Customer.objects.create(**validated_data)

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
