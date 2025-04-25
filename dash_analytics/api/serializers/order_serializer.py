from rest_framework import serializers
from core.models import Order, OrderItem, Product, Customer
from .product_serializer import ProductSerializer


class OrderItemSerializer(serializers.Serializer):
    product = serializers.CharField()
    quantity = serializers.IntegerField(min_value=1)
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    discount = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, default=0)

    def to_representation(self, instance):
        ret = super().to_representation(instance)

        # Replace product ID with product details
        if isinstance(instance.product, Product):
            from .product_serializer import ProductSerializer
            ret['product'] = ProductSerializer(instance.product).data

        return ret


class OrderSerializer(serializers.Serializer):
    id = serializers.CharField(source='id')
    order_id = serializers.CharField()
    customer = serializers.CharField()
    order_date = serializers.DateTimeField()
    items = OrderItemSerializer(many=True)
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    payment_method = serializers.CharField(required=False, allow_null=True)
    shipping_address = serializers.CharField(required=False, allow_null=True)
    order_status = serializers.CharField()
    delivery_date = serializers.DateTimeField(required=False, allow_null=True)

    def to_representation(self, instance):
        ret = super().to_representation(instance)

        # Replace customer ID with customer details
        if isinstance(instance.customer, Customer):
            from .customer_serializer import CustomerSerializer
            ret['customer'] = CustomerSerializer(instance.customer).data

        return ret

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        order = Order.objects.create(**validated_data)

        for item_data in items_data:
            product = Product.objects.get(id=item_data['product'])
            OrderItem(product=product, **item_data).save()

        return order

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if items_data:
            # Clear existing items and create new ones
            instance.items.clear()
            for item_data in items_data:
                product = Product.objects.get(id=item_data['product'])
                item_data['product'] = product
                instance.items.append(OrderItem(**item_data))

        instance.save()
        return instance
