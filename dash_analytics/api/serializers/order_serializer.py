from rest_framework import serializers
from core.models import Order, Product, Customer
from .product_serializer import ProductSerializer

class OrderSerializer(serializers.Serializer):
    id = serializers.CharField(source='id')
    order_id = serializers.CharField()
    customer = serializers.CharField()
    order_date = serializers.DateTimeField()
    quantity = serializers.IntegerField()
    payment_method = serializers.CharField(required=False, allow_null=True)
    review_score = serializers.FloatField(required=False, allow_null=True)
    customer_id = serializers.CharField()
    product_id = serializers.CharField()

    def to_representation(self, instance):
        ret = super().to_representation(instance)

        # Replace customer ID with customer details
        if isinstance(instance.customer_id, Customer):
            from .customer_serializer import CustomerSerializer
            ret['customer'] = CustomerSerializer(instance.customer_id).data

        # Replace product ID with product details
        if isinstance(instance.product_id, Product):
            ret['product'] = ProductSerializer(instance.product_id).data

        return ret

    def create(self, validated_data):
        order = Order.objects.create(**validated_data)
        return order

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
