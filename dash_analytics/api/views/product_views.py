from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Avg, F, Count
from django.db.models.functions import TruncDate
from core.models import Product, Order, OrderItem
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
            {"$unwind": "$items"},
            {"$group": {
                "_id": "$items.product",
                "total_quantity": {"$sum": "$items.quantity"},
                "total_revenue": {"$sum": {"$multiply": ["$items.price", "$items.quantity"]}},
                "orders_count": {"$sum": 1},
            }}
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
            {"$unwind": "$items"},
            {"$group": {
                "_id": "$items.product",
                "total_quantity": {"$sum": "$items.quantity"},
                "total_revenue": {"$sum": {"$multiply": ["$items.price", "$items.quantity"]}},
            }},
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
    base_query = OrderItem.objects.filter(order__status='completed')
    if start_date:
        base_query = base_query.filter(order__order_date__gte=start_date)
    if category != 'all':
        base_query = base_query.filter(product__category=category)
    
    # Best selling products (by revenue)
    best_selling = (base_query
        .values('product__name')
        .annotate(
            revenue=Sum(F('quantity') * F('unit_price')),
            name=F('product__name')
        )
        .order_by('-revenue')[:10])
    
    # Category performance
    category_performance = (base_query
        .values('product__category')
        .annotate(
            category=F('product__category'),
            total_sales=Sum(F('quantity') * F('unit_price'))
        )
        .order_by('-total_sales'))
    
    # Volume metrics
    volume_data = (base_query
        .values('product__name')
        .annotate(
            name=F('product__name'),
            quantity=Sum('quantity')
        )
        .order_by('-quantity')[:10])
    
    # Average revenue per product
    avg_revenue = (base_query
        .values('product__name')
        .annotate(
            name=F('product__name'),
            avg_revenue=Avg(F('quantity') * F('unit_price'))
        )
        .order_by('-avg_revenue')[:10])
    
    # Calculate growth rates and trends
    if start_date:
        mid_date = start_date + (end_date - start_date) / 2
        recent_sales = base_query.filter(order__order_date__gte=mid_date)
        older_sales = base_query.filter(order__order_date__lt=mid_date)
    
    # Best product metrics
    best_product = list(best_selling)[0] if best_selling else None
    if best_product:
        if start_date:
            recent_revenue = recent_sales.filter(
                product__name=best_product['name']
            ).aggregate(
                revenue=Sum(F('quantity') * F('unit_price'))
            )['revenue'] or 0
            
            older_revenue = older_sales.filter(
                product__name=best_product['name']
            ).aggregate(
                revenue=Sum(F('quantity') * F('unit_price'))
            )['revenue'] or 0
            
            growth = ((recent_revenue - older_revenue) / older_revenue * 100) if older_revenue else 0
            best_product['growth'] = round(growth, 1)
    
    # Top category metrics
    top_category = list(category_performance)[0] if category_performance else None
    if top_category:
        total_sales = sum(cat['total_sales'] for cat in category_performance)
        top_category['market_share'] = round((top_category['total_sales'] / total_sales) * 100, 1)
    
    # Top volume product metrics
    top_volume = list(volume_data)[0] if volume_data else None
    if top_volume:
        total_volume = sum(prod['quantity'] for prod in volume_data)
        top_volume['percentage'] = round((top_volume['quantity'] / total_volume) * 100, 1)
    
    # Detailed product performance
    detailed_performance = []
    for product in best_selling[:20]:  # Top 20 products
        if start_date:
            recent_data = recent_sales.filter(
                product__name=product['name']
            ).aggregate(
                revenue=Sum(F('quantity') * F('unit_price')),
                units=Sum('quantity')
            )
            
            older_data = older_sales.filter(
                product__name=product['name']
            ).aggregate(
                revenue=Sum(F('quantity') * F('unit_price')),
                units=Sum('quantity')
            )
            
            trend = ((recent_data['revenue'] or 0) - (older_data['revenue'] or 0)) / (older_data['revenue'] or 1) * 100
        else:
            trend = 0
            
        product_details = base_query.filter(
            product__name=product['name']
        ).aggregate(
            units_sold=Sum('quantity'),
            total_revenue=Sum(F('quantity') * F('unit_price')),
            avg_price=Avg('unit_price')
        )
        
        detailed_performance.append({
            'name': product['name'],
            'category': base_query.filter(product__name=product['name']).first().product.category,
            'units_sold': product_details['units_sold'],
            'revenue': product_details['total_revenue'],
            'avg_price': product_details['avg_price'],
            'trend': round(trend, 1)
        })
    
    return Response({
        'best_selling': list(best_selling),
        'category_performance': list(category_performance),
        'volume_data': list(volume_data),
        'avg_revenue': list(avg_revenue),
        'best_product': best_product,
        'top_category': top_category,
        'top_volume': top_volume,
        'detailed_performance': detailed_performance
    })