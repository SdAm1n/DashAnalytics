from rest_framework import serializers
from core.models import Product


class ProductSerializer(serializers.Serializer):
    id = serializers.CharField(source='id')
    product_id = serializers.CharField()
    name = serializers.CharField()
    category = serializers.CharField()
    sub_category = serializers.CharField(required=False, allow_null=True)
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    cost = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True)
    description = serializers.CharField(required=False, allow_null=True)
    stock_quantity = serializers.IntegerField(required=False, default=0)
    rating = serializers.FloatField(required=False, allow_null=True)
    listing_date = serializers.DateTimeField(required=False, allow_null=True)

    def create(self, validated_data):
        return Product.objects.create(**validated_data)

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
