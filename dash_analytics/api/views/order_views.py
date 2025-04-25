from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from core.models import Order
from api.serializers import OrderSerializer
from django.http import Http404
import datetime

class OrderViewSet(viewsets.ViewSet):
    """
    API endpoint for orders
    """

    def list(self, request):
        orders = Order.objects.all()
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        try:
            order = Order.objects.get(id=pk)
        except Order.DoesNotExist:
            raise Http404

        serializer = OrderSerializer(order)
        return Response(serializer.data)

    def create(self, request):
        serializer = OrderSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None):
        try:
            order = Order.objects.get(id=pk)
        except Order.DoesNotExist:
            raise Http404

        serializer = OrderSerializer(order, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        try:
            order = Order.objects.get(id=pk)
        except Order.DoesNotExist:
            raise Http404

        serializer = OrderSerializer(order, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        try:
            order = Order.objects.get(id=pk)
        except Order.DoesNotExist:
            raise Http404

        order.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'])
    def sales_trend(self, request):
        """
        Get sales trend data for visualization
        """
        period = request.query_params.get('period', 'monthly')

        # Create the appropriate time grouping query
        if period == 'daily':
            time_group = {
                "year": {"$year": "$order_date"},
                "month": {"$month": "$order_date"},
                "day": {"$dayOfMonth": "$order_date"}
            }
        elif period == 'weekly':
            time_group = {
                "year": {"$year": "$order_date"},
                "week": {"$week": "$order_date"}
            }
        elif period == 'monthly':
            time_group = {
                "year": {"$year": "$order_date"},
                "month": {"$month": "$order_date"}
            }
        elif period == 'quarterly':
            time_group = {
                "year": {"$year": "$order_date"},
                "quarter": {"$ceil": {"$divide": [{"$month": "$order_date"}, 3]}}
            }
        else:  # yearly
            time_group = {
                "year": {"$year": "$order_date"}
            }

        # Get sales data grouped by time period
        sales_trend = Order.objects.aggregate([
            {"$group": {
                "_id": time_group,
                "total_sales": {"$sum": "$total_amount"},
                "order_count": {"$sum": 1}
            }},
            {"$sort": {"_id.year": 1, "_id.month": 1,
                       "_id.day": 1, "_id.week": 1, "_id.quarter": 1}}
        ])

        # Format data for frontend charts
        result = []
        for item in sales_trend:
            time_id = item['_id']

            if period == 'daily':
                label = f"{time_id['year']}-{time_id['month']:02d}-{time_id['day']:02d}"
            elif period == 'weekly':
                label = f"{time_id['year']} Week {time_id['week']}"
            elif period == 'monthly':
                label = f"{time_id['year']}-{time_id['month']:02d}"
            elif period == 'quarterly':
                label = f"{time_id['year']} Q{time_id['quarter']}"
            else:  # yearly
                label = f"{time_id['year']}"

            result.append({
                'period': label,
                'total_sales': float(item['total_sales']),
                'order_count': item['order_count']
            })

        return Response(result)

    @action(detail=False, methods=['get'])
    def recent(self, request):
        """
        Get most recent orders
        """
        limit = int(request.query_params.get('limit', 10))
        orders = Order.objects.order_by('-order_date')[:limit]

        result = []
        for order in orders:
            customer_name = order.customer.name if order.customer else "Unknown"

            result.append({
                'order_id': order.order_id,
                'customer_name': customer_name,
                'date': order.order_date,
                'total': float(order.total_amount),
                'status': order.order_status,
                'item_count': len(order.items) if order.items else 0
            })

        return Response(result)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Get order statistics
        """
        # Get total orders
        total_orders = Order.objects.count()

        # Get total revenue
        total_revenue = Order.objects.aggregate(
            total={"$sum": "$total_amount"})
        total_revenue = total_revenue['total'] if 'total' in total_revenue else 0

        # Get average order value
        avg_order_value = Order.objects.aggregate(
            avg={"$avg": "$total_amount"})
        avg_order_value = avg_order_value['avg'] if 'avg' in avg_order_value else 0

        # Get orders by status
        status_counts = Order.objects.aggregate([
            {"$group": {
                "_id": "$order_status",
                "count": {"$sum": 1}
            }}
        ])

        # Get today's orders
        today = datetime.datetime.now().replace(
            hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + datetime.timedelta(days=1)

        today_orders = Order.objects.filter(
            order_date__gte=today, order_date__lt=tomorrow).count()
        today_revenue = Order.objects.filter(
            order_date__gte=today, order_date__lt=tomorrow).aggregate(total={"$sum": "$total_amount"})
        today_revenue = today_revenue['total'] if 'total' in today_revenue else 0

        return Response({
            'total_orders': total_orders,
            'total_revenue': float(total_revenue),
            'avg_order_value': float(avg_order_value),
            'today_orders': today_orders,
            'today_revenue': float(today_revenue),
            'status_counts': list(status_counts)
        })