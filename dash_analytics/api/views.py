from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from core.models import Customer, Product, Order, RawDataUpload
from analytics.models import Analysis, Prediction, ProductCorrelation, CustomerSegment
from .serializers import (
    CustomerSerializer, ProductSerializer, OrderSerializer,
    AnalysisSerializer, PredictionSerializer
)
from django.http import Http404
import datetime
import uuid


class CustomerViewSet(viewsets.ViewSet):
    """
    API endpoint for customers
    """

    def list(self, request):
        customers = Customer.objects.all()
        serializer = CustomerSerializer(customers, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        try:
            customer = Customer.objects.get(id=pk)
        except Customer.DoesNotExist:
            raise Http404

        serializer = CustomerSerializer(customer)
        return Response(serializer.data)

    def create(self, request):
        serializer = CustomerSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None):
        try:
            customer = Customer.objects.get(id=pk)
        except Customer.DoesNotExist:
            raise Http404

        serializer = CustomerSerializer(customer, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        try:
            customer = Customer.objects.get(id=pk)
        except Customer.DoesNotExist:
            raise Http404

        serializer = CustomerSerializer(
            customer, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        try:
            customer = Customer.objects.get(id=pk)
        except Customer.DoesNotExist:
            raise Http404

        customer.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'])
    def demographics(self, request):
        """
        Get customer demographics data for visualization
        """
        # Get age distribution
        age_distribution = Customer.objects.aggregate({
            "$group": {
                "_id": {
                    "$concat": [
                        {"$cond": [{"$lt": ["$age", 18]}, "Under 18", ""]},
                        {"$cond": [{"$and": [{"$gte": ["$age", 18]},
                                             {"$lt": ["$age", 25]}]}, "18-24", ""]},
                        {"$cond": [{"$and": [{"$gte": ["$age", 25]},
                                             {"$lt": ["$age", 35]}]}, "25-34", ""]},
                        {"$cond": [{"$and": [{"$gte": ["$age", 35]},
                                             {"$lt": ["$age", 45]}]}, "35-44", ""]},
                        {"$cond": [{"$and": [{"$gte": ["$age", 45]},
                                             {"$lt": ["$age", 55]}]}, "45-54", ""]},
                        {"$cond": [{"$and": [{"$gte": ["$age", 55]},
                                             {"$lt": ["$age", 65]}]}, "55-64", ""]},
                        {"$cond": [{"$gte": ["$age", 65]}, "65+", ""]},
                    ]
                },
                "count": {"$sum": 1}
            }
        })

        # Get gender distribution
        gender_distribution = Customer.objects.aggregate({
            "$group": {
                "_id": "$gender",
                "count": {"$sum": 1}
            }
        })

        # Get location distribution
        location_distribution = Customer.objects.aggregate({
            "$group": {
                "_id": "$location",
                "count": {"$sum": 1}
            }
        })

        return Response({
            'age_distribution': list(age_distribution),
            'gender_distribution': list(gender_distribution),
            'location_distribution': list(location_distribution)
        })

    @action(detail=True, methods=['get'])
    def purchase_history(self, request, pk=None):
        """
        Get purchase history for a specific customer
        """
        try:
            customer = Customer.objects.get(id=pk)
        except Customer.DoesNotExist:
            raise Http404

        orders = Order.objects.filter(
            customer=customer).order_by('-order_date')
        data = []

        for order in orders:
            order_data = {
                'order_id': order.order_id,
                'date': order.order_date,
                'total': order.total_amount,
                'status': order.order_status,
                'items': []
            }

            for item in order.items:
                order_data['items'].append({
                    'product_name': item.product.name,
                    'quantity': item.quantity,
                    'price': item.price,
                    'subtotal': item.price * item.quantity - item.discount
                })

            data.append(order_data)

        return Response(data)


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

        serializer = ProductSerializer(
            product, data=request.data, partial=True)
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
        # Get period from query parameters
        period = request.query_params.get('period', 'monthly')

        # Create the appropriate time grouping query
        if period == 'daily':
            time_group = {
                "year": {"$year": "$order_date"},
                "month": {"$month": "$order_date"},
                "day": {"$dayOfMonth": "$order_date"}
            }
            time_format = "%Y-%m-%d"
        elif period == 'weekly':
            time_group = {
                "year": {"$year": "$order_date"},
                "week": {"$week": "$order_date"}
            }
            time_format = "Week %V, %Y"
        elif period == 'monthly':
            time_group = {
                "year": {"$year": "$order_date"},
                "month": {"$month": "$order_date"}
            }
            time_format = "%Y-%m"
        elif period == 'quarterly':
            time_group = {
                "year": {"$year": "$order_date"},
                "quarter": {"$ceil": {"$divide": [{"$month": "$order_date"}, 3]}}
            }
            time_format = "Q%q %Y"
        else:  # yearly
            time_group = {
                "year": {"$year": "$order_date"}
            }
            time_format = "%Y"

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


class AnalyticsViewSet(viewsets.ViewSet):
    """
    API endpoint for analytics and predictions
    """

    @action(detail=False, methods=['get'])
    def analyses(self, request):
        """
        Get all analyses
        """
        analysis_type = request.query_params.get('type', None)

        if analysis_type:
            analyses = Analysis.objects.filter(analysis_type=analysis_type)
        else:
            analyses = Analysis.objects.all()

        serializer = AnalysisSerializer(analyses, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def analysis_detail(self, request, pk=None):
        """
        Get a specific analysis
        """
        try:
            analysis = Analysis.objects.get(id=pk)
        except Analysis.DoesNotExist:
            raise Http404

        serializer = AnalysisSerializer(analysis)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def predictions(self, request):
        """
        Get all predictions
        """
        prediction_type = request.query_params.get('type', None)

        if prediction_type:
            predictions = Prediction.objects.filter(
                prediction_type=prediction_type)
        else:
            predictions = Prediction.objects.all()

        serializer = PredictionSerializer(predictions, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def prediction_detail(self, request, pk=None):
        """
        Get a specific prediction
        """
        try:
            prediction = Prediction.objects.get(id=pk)
        except Prediction.DoesNotExist:
            raise Http404

        serializer = PredictionSerializer(prediction)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def customer_segments(self, request):
        """
        Get customer segmentation data
        """
        segments = CustomerSegment.objects.all()

        result = []
        for segment in segments:
            result.append({
                'segment_id': segment.segment_id,
                'segment_name': segment.segment_name,
                'customer_count': segment.customer_count,
                'average_purchase_value': float(segment.average_purchase_value),
                'criteria': segment.criteria
            })

        return Response(result)

    @action(detail=False, methods=['get'])
    def product_correlations(self, request):
        """
        Get product correlation data
        """
        min_score = float(request.query_params.get('min_score', 0.5))

        correlations = ProductCorrelation.objects.filter(
            correlation_score__gte=min_score)

        result = []
        for corr in correlations:
            try:
                product_a = Product.objects.get(product_id=corr.product_a_id)
                product_b = Product.objects.get(product_id=corr.product_b_id)

                result.append({
                    'product_a': {
                        'product_id': product_a.product_id,
                        'name': product_a.name,
                        'category': product_a.category
                    },
                    'product_b': {
                        'product_id': product_b.product_id,
                        'name': product_b.name,
                        'category': product_b.category
                    },
                    'correlation_score': corr.correlation_score
                })
            except (Product.DoesNotExist, AttributeError):
                pass

        return Response(sorted(result, key=lambda x: x['correlation_score'], reverse=True))

    @action(detail=False, methods=['get'])
    def dashboard_summary(self, request):
        """
        Get dashboard summary data
        """
        # Get total customers
        total_customers = Customer.objects.count()

        # Get total products
        total_products = Product.objects.count()

        # Get total orders
        total_orders = Order.objects.count()

        # Get total revenue
        total_revenue = Order.objects.aggregate(
            total={"$sum": "$total_amount"})
        total_revenue = total_revenue.get('total', 0)

        # Get recent orders (last 5)
        recent_orders = Order.objects.order_by('-order_date')[:5]
        recent_orders_data = []

        for order in recent_orders:
            customer_name = order.customer.name if order.customer else "Unknown"
            recent_orders_data.append({
                'order_id': order.order_id,
                'customer_name': customer_name,
                'date': order.order_date,
                'total': float(order.total_amount)
            })

        # Get top selling products
        top_products = Order.objects.aggregate([
            {"$unwind": "$items"},
            {"$group": {
                "_id": "$items.product",
                "total_quantity": {"$sum": "$items.quantity"}
            }},
            {"$sort": {"total_quantity": -1}},
            {"$limit": 5}
        ])

        top_products_data = []
        for product in top_products:
            try:
                p = Product.objects.get(id=product['_id'])
                top_products_data.append({
                    'name': p.name,
                    'quantity': product['total_quantity']
                })
            except Product.DoesNotExist:
                pass

        return Response({
            'total_customers': total_customers,
            'total_products': total_products,
            'total_orders': total_orders,
            'total_revenue': float(total_revenue),
            'recent_orders': recent_orders_data,
            'top_products': top_products_data
        })


class DataUploadViewSet(viewsets.ViewSet):
    """
    API endpoint for data uploads and processing
    """

    def list(self, request):
        """
        List all data uploads
        """
        uploads = RawDataUpload.objects.all().order_by('-upload_date')

        result = []
        for upload in uploads:
            result.append({
                'id': str(upload.id),
                'file_name': upload.file_name,
                'upload_date': upload.upload_date,
                'file_size': upload.file_size,
                'row_count': upload.row_count,
                'processed': upload.processed,
                'processed_date': upload.processed_date
            })

        return Response(result)

    def retrieve(self, request, pk=None):
        """
        Get details of a specific upload
        """
        try:
            upload = RawDataUpload.objects.get(id=pk)
        except RawDataUpload.DoesNotExist:
            raise Http404

        return Response({
            'id': str(upload.id),
            'file_name': upload.file_name,
            'upload_date': upload.upload_date,
            'file_size': upload.file_size,
            'row_count': upload.row_count,
            'processed': upload.processed,
            'processed_date': upload.processed_date
        })

    @action(detail=False, methods=['post'])
    def upload_csv(self, request):
        """
        Upload a CSV file for processing
        """
        if 'file' not in request.FILES:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

        csv_file = request.FILES['file']

        if not csv_file.name.endswith('.csv'):
            return Response({'error': 'File must be a CSV'}, status=status.HTTP_400_BAD_REQUEST)

        # Save the uploaded file
        # Code to save the file and create a RawDataUpload record
        # This will be implemented in a separate file service

        return Response({'message': 'File uploaded successfully'}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def process(self, request, pk=None):
        """
        Process a previously uploaded CSV file
        """
        try:
            upload = RawDataUpload.objects.get(id=pk)
        except RawDataUpload.DoesNotExist:
            raise Http404

        if upload.processed:
            return Response({'error': 'This file has already been processed'}, status=status.HTTP_400_BAD_REQUEST)

        # Code to process the CSV file and populate the database
        # This will be implemented in a separate data processing service

        # Update the upload record
        upload.processed = True
        upload.processed_date = datetime.datetime.now()
        upload.save()

        return Response({'message': 'File processing started'}, status=status.HTTP_202_ACCEPTED)
