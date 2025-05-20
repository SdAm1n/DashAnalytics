from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from core.models import Order, Sales
from api.serializers import OrderSerializer
from django.http import Http404
import datetime
import pandas as pd
from django.utils import timezone
from datetime import timedelta


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
        Get sales trend data for the dashboard
        """
        from datetime import datetime, timedelta
        from dateutil.relativedelta import relativedelta
        import pandas as pd

        # Get period parameter (default to week)
        period = request.query_params.get('period', 'week')

        # Define time periods based on the selected period
        end_date = datetime.now()
        if period == 'week':
            # Get data for the last 7 days
            start_date = end_date - timedelta(days=7)
            # Format for daily data points
            format_str = '%Y-%m-%d'
            date_list = [(start_date + timedelta(days=i)
                          ).strftime(format_str) for i in range(8)]
        elif period == 'month':
            # Get data for the last 30 days
            start_date = end_date - timedelta(days=30)
            # Format for weekly data points
            format_str = '%Y-%m-%d'
            date_list = [(start_date + timedelta(days=i*7)
                          ).strftime(format_str) for i in range(5)]
        elif period == 'year':
            # Get data for the last 12 months
            start_date = end_date - relativedelta(months=12)
            # Format for monthly data points
            format_str = '%Y-%m'
            date_list = [(end_date - relativedelta(months=i)
                          ).strftime(format_str) for i in range(12, -1, -1)]
        else:
            # Default to week if not recognized
            start_date = end_date - timedelta(days=7)
            format_str = '%Y-%m-%d'
            date_list = [(start_date + timedelta(days=i)
                          ).strftime(format_str) for i in range(8)]

        # Query orders within the date range
        try:
            if period == 'year':
                # For yearly data, we need to query by month
                orders = Order.objects.filter(order_date__gte=start_date)

                # Convert to pandas DataFrame for easier manipulation
                orders_data = []
                for order in orders:
                    orders_data.append({
                        'order_id': str(order.order_id),
                        'order_date': order.order_date,
                        'quantity': order.quantity,
                        'total_amount': order.quantity * float(order.product_id.price if hasattr(order.product_id, 'price') else 0)
                    })

                df = pd.DataFrame(orders_data)

                # Extract month from dates and group by month
                if not df.empty:
                    df['period'] = df['order_date'].dt.strftime('%Y-%m')
                    monthly_data = df.groupby('period').agg(
                        total_sales=('total_amount', 'sum'),
                        order_count=('order_id', 'count')
                    ).reset_index()

                    # Create dictionary mapping month to data
                    data_dict = {row['period']: {
                        'total_sales': float(row['total_sales']),
                        'order_count': int(row['order_count'])
                    } for _, row in monthly_data.iterrows()}

                    # Create result with all months in the period
                    result = []
                    for date_str in date_list:
                        period_data = data_dict.get(
                            date_str, {'total_sales': 0, 'order_count': 0})
                        result.append({
                            'period': date_str,
                            'total_sales': period_data['total_sales'],
                            'order_count': period_data['order_count']
                        })
                else:
                    # No data found
                    result = [{'period': date, 'total_sales': 0,
                               'order_count': 0} for date in date_list]
            else:
                # For weekly or daily data
                orders = Order.objects.filter(order_date__gte=start_date)

                # Convert to pandas DataFrame
                orders_data = []
                for order in orders:
                    orders_data.append({
                        'order_id': str(order.order_id),
                        'order_date': order.order_date,
                        'quantity': order.quantity,
                        'total_amount': order.quantity * float(order.product_id.price if hasattr(order.product_id, 'price') else 0)
                    })

                df = pd.DataFrame(orders_data)

                # Format dates and group
                if not df.empty:
                    df['period'] = df['order_date'].dt.strftime(format_str)
                    daily_data = df.groupby('period').agg(
                        total_sales=('total_amount', 'sum'),
                        order_count=('order_id', 'count')
                    ).reset_index()

                    # Create dictionary mapping date to data
                    data_dict = {row['period']: {
                        'total_sales': float(row['total_sales']),
                        'order_count': int(row['order_count'])
                    } for _, row in daily_data.iterrows()}

                    # Create result with all dates in the period
                    result = []
                    for date_str in date_list:
                        period_data = data_dict.get(
                            date_str, {'total_sales': 0, 'order_count': 0})
                        result.append({
                            'period': date_str,
                            'total_sales': period_data['total_sales'],
                            'order_count': period_data['order_count']
                        })
                else:
                    # No data found
                    result = [{'period': date, 'total_sales': 0,
                               'order_count': 0} for date in date_list]

            return Response(result)
        except Exception as e:
            return Response(
                {'error': f'Error retrieving sales trend data: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def recent(self, request):
        """
        Get most recent orders
        """
        limit = int(request.query_params.get('limit', 10))
        orders = Order.objects.order_by('-order_date')[:limit]

        result = []
        for order in orders:
            customer_id = order.customer.customer_id if order.customer else "Unknown"

            result.append({
                'order_id': order.order_id,
                'customer_id': customer_id,
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
