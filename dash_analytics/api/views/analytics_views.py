from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db.models import Sum
from core.models import Customer, Product, Order
from analytics.models import Analysis, Prediction, ProductCorrelation, CustomerSegment
from api.serializers import AnalysisSerializer, PredictionSerializer
from django.http import Http404

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
            predictions = Prediction.objects.filter(prediction_type=prediction_type)
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

        correlations = ProductCorrelation.objects.filter(correlation_score__gte=min_score)

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

        # Get total revenue using MongoDB aggregation pipeline
        total_revenue_agg = Order.objects.aggregate([
            {"$group": {
                "_id": None,
                "total": {"$sum": "$total_amount"}
            }}
        ])
        total_revenue = next(total_revenue_agg).get('total', 0) if total_revenue_agg else 0

        # Get recent orders (last 5)
        recent_orders = Order.objects.order_by('-order_date')[:5]
        recent_orders_data = []

        for order in recent_orders:
            customer_name = order.customer.name if order.customer else "Unknown"
            recent_orders_data.append({
                'order_id': order.order_id,
                'customer_name': customer_name,
                'date': order.order_date,
                'total': float(order.total_amount),
                'status': order.order_status
            })

        # Get top products
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
                continue

        return Response({
            'total_customers': total_customers,
            'total_products': total_products,
            'total_orders': total_orders,
            'total_revenue': float(total_revenue),
            'recent_orders': recent_orders_data,
            'top_products': top_products_data
        })