from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Avg, F, Count
from django.db.models.functions import TruncDate
from core.models import Product, Order
from api.serializers import ProductSerializer
from django.http import Http404
from datetime import datetime, timedelta

class ProductViewSet(viewsets.ViewSet):
    """
    API endpoint for products
    """

    def list(self, request):
        products = Product.objects.all()
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        try:
            product = Product.objects.get(id=pk)
        except Product.DoesNotExist:
            raise Http404

        serializer = ProductSerializer(product)
        return Response(serializer.data)

    def create(self, request):
        serializer = ProductSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None):
        try:
            product = Product.objects.get(id=pk)
        except Product.DoesNotExist:
            raise Http404

        serializer = ProductSerializer(product, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        try:
            product = Product.objects.get(id=pk)
        except Product.DoesNotExist:
            raise Http404

        serializer = ProductSerializer(product, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        try:
            product = Product.objects.get(id=pk)
        except Product.DoesNotExist:
            raise Http404

        product.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'])
    def categories(self, request):
        """
        Get all product categories and subcategories
        """
        categories = Product.objects.aggregate({
            "$group": {
                "_id": {
                    "category": "$category",
                    "sub_category": "$sub_category"
                },
                "count": {"$sum": 1}
            }
        })

        # Reorganize data for frontend
        result = {}
        for item in categories:
            category = item['_id']['category']
            sub_category = item['_id']['sub_category']
            count = item['count']

            if category not in result:
                result[category] = {'total': 0, 'subcategories': {}}

            result[category]['total'] += count

            if sub_category:
                if sub_category not in result[category]['subcategories']:
                    result[category]['subcategories'][sub_category] = 0
                result[category]['subcategories'][sub_category] += count

        return Response(result)

    @action(detail=False, methods=['get'])
    def performance(self, request):
        """
        Get product performance metrics
        """
        # Get total sales per product
        product_sales = Order.objects.aggregate([
            {
                "$group": {
                    "_id": "$product_id",
                    "total_quantity": {"$sum": "$quantity"},
                    "total_revenue": {"$sum": {"$multiply": ["$quantity", "$product_id.price"]}},
                    "orders_count": {"$sum": 1},
                }
            }
        ])

        # Enhance with product details
        result = []
        for sale in product_sales:
            try:
                product = Product.objects.get(id=sale['_id'])
                result.append({
                    'product_id': str(product.id),
                    'product_name': product.name,
                    'category': product.category,
                    'total_quantity': sale['total_quantity'],
                    'total_revenue': float(sale['total_revenue']),
                    'orders_count': sale['orders_count'],
                    'avg_price': float(product.price),
                    'rating': product.rating
                })
            except Product.DoesNotExist:
                pass

        return Response(result)

    @action(detail=False, methods=['get'])
    def top_sellers(self, request):
        """
        Get top selling products
        """
        limit = int(request.query_params.get('limit', 10))

        # Get top sellers by quantity
        top_sellers = Order.objects.aggregate([
            {
                "$group": {
                    "_id": "$product_id",
                    "total_quantity": {"$sum": "$quantity"},
                    "total_revenue": {"$sum": {"$multiply": ["$quantity", "$product_id.price"]}},
                }
            },
            {"$sort": {"total_quantity": -1}},
            {"$limit": limit}
        ])

        # Enhance with product details
        result = []
        for sale in top_sellers:
            try:
                product = Product.objects.get(id=sale['_id'])
                result.append({
                    'product_id': str(product.id),
                    'product_name': product.name,
                    'category': product.category,
                    'total_quantity': sale['total_quantity'],
                    'total_revenue': float(sale['total_revenue'])
                })
            except Product.DoesNotExist:
                pass

        return Response(result)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_product_performance(request):
    period = request.GET.get('period', '1y')
    category = request.GET.get('category', 'all')
    
    # Calculate date range
    end_date = datetime.now()
    if period == '7d':
        start_date = end_date - timedelta(days=7)
    elif period == '30d':
        start_date = end_date - timedelta(days=30)
    elif period == '90d':
        start_date = end_date - timedelta(days=90)
    elif period == '1y':
        start_date = end_date - timedelta(days=365)
    else:  # 'all'
        start_date = None
    
    # Base query
    base_query = Order.objects
    if start_date:
        base_query = base_query.filter(order_date__gte=start_date)
    
    # Best selling products (by quantity)
    best_selling = list(base_query.aggregate([
        {
            '$group': {
                '_id': '$product_id',
                'total_quantity': {'$sum': '$quantity'},
                'avg_revenue': {'$avg': {'$multiply': ['$quantity', {'$arrayElemAt': ['$product_id.price', 0]}]}}
            }
        },
        {'$sort': {'total_quantity': -1}},
        {'$limit': 10}
    ]))
    
    # Calculate growth rates and trends
    product_trends = {}
    if start_date:
        mid_date = start_date + (end_date - start_date) / 2
        for product in best_selling:
            recent_sales = base_query.filter(
                product_id=product['_id'],
                order_date__gte=mid_date
            ).aggregate(total={'$sum': '$quantity'})['total'] or 0
            
            older_sales = base_query.filter(
                product_id=product['_id'],
                order_date__lt=mid_date
            ).aggregate(total={'$sum': '$quantity'})['total'] or 0
            
            if older_sales > 0:
                growth = ((recent_sales - older_sales) / older_sales) * 100
            else:
                growth = 0
            
            product_trends[str(product['_id'])] = growth

    response_data = {
        'best_selling': best_selling,
        'trends': product_trends
    }
    
    return Response(response_data)