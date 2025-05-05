from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db.models import Sum, Avg, Count, Case, When, Value, CharField
from django.utils import timezone
from datetime import timedelta
from core.models import Customer, Product, Order
from api.serializers.analysis_serializer import (
    SalesTrendSerializer, 
    GeographicalInsightSerializer,
    CustomerAnalyticsSerializer
)
from django.http import Http404
from django.db.models import Count, Sum
from rest_framework.views import APIView

class AnalyticsViewSet(viewsets.ViewSet):
    """
    API endpoint for analytics and predictions
    """

    @action(detail=False, methods=['GET'])
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

    @action(detail=False, methods=['GET'])
    def demographics(self, request):
        """Get demographic analysis data"""
        period = request.query_params.get('period', '1y')
        
        # Calculate date range
        end_date = timezone.now()
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
        query = Order.objects.filter(status='completed')
        if start_date:
            query = query.filter(order_date__gte=start_date)

        # Define age groups
        age_bins = [0, 18, 30, 40, 50, 60, 100]
        age_labels = ['<18', '18-30', '30-40', '40-50', '50-60', '60+']

        # Calculate age distribution
        customers = Customer.objects.annotate(
            age_group=Case(
                *[When(age__gt=age_bins[i], age__lte=age_bins[i+1], then=Value(age_labels[i]))
                  for i in range(len(age_bins)-1)],
                default=Value('Unknown'),
                output_field=CharField(),
            )
        )

        age_distribution = customers.values('age_group').annotate(
            count=Count('id')
        ).order_by('age_group')

        # Gender distribution
        gender_counts = customers.values('gender').annotate(
            count=Count('id')
        )
        total_customers = customers.count()
        gender_distribution = {
            'male': next((item['count'] for item in gender_counts if item['gender'] == 'M'), 0),
            'female': next((item['count'] for item in gender_counts if item['gender'] == 'F'), 0)
        }

        # Gender by age distribution
        gender_age_dist = customers.values('age_group', 'gender').annotate(
            count=Count('id')
        ).order_by('age_group', 'gender')

        # Process gender-age distribution
        gender_age_data = {
            'age_groups': age_labels,
            'male': [0] * len(age_labels),
            'female': [0] * len(age_labels)
        }

        for item in gender_age_dist:
            if item['age_group'] in age_labels:
                idx = age_labels.index(item['age_group'])
                if item['gender'] == 'M':
                    gender_age_data['male'][idx] = item['count']
                elif item['gender'] == 'F':
                    gender_age_data['female'][idx] = item['count']

        # Sales analysis by age group
        age_sales = Order.objects.filter(
            status='completed'
        ).annotate(
            age_group=Case(
                *[When(customer__age__gt=age_bins[i], customer__age__lte=age_bins[i+1], 
                       then=Value(age_labels[i]))
                  for i in range(len(age_bins)-1)],
                default=Value('Unknown'),
                output_field=CharField(),
            )
        ).values('age_group').annotate(
            total_sales=Sum('total_amount')
        ).order_by('age_group')

        # Sales by gender and age
        gender_age_sales = Order.objects.filter(
            status='completed'
        ).annotate(
            age_group=Case(
                *[When(customer__age__gt=age_bins[i], customer__age__lte=age_bins[i+1],
                       then=Value(age_labels[i]))
                  for i in range(len(age_bins)-1)],
                default=Value('Unknown'),
                output_field=CharField(),
            )
        ).values('age_group', 'customer__gender').annotate(
            total_sales=Sum('total_amount')
        ).order_by('age_group', 'customer__gender')

        # Process gender-age sales data
        sales_by_gender_age = {
            'age_groups': age_labels,
            'male_sales': [0] * len(age_labels),
            'female_sales': [0] * len(age_labels)
        }

        for item in gender_age_sales:
            if item['age_group'] in age_labels:
                idx = age_labels.index(item['age_group'])
                if item['customer__gender'] == 'M':
                    sales_by_gender_age['male_sales'][idx] = float(item['total_sales'])
                elif item['customer__gender'] == 'F':
                    sales_by_gender_age['female_sales'][idx] = float(item['total_sales'])

        # Calculate key metrics
        avg_age = customers.aggregate(Avg('age'))['age__avg']
        gender_ratio = (gender_distribution['male'] / gender_distribution['female'] 
                       if gender_distribution['female'] > 0 else 0)

        # Find most active age group by transaction volume
        most_active = Order.objects.filter(
            status='completed'
        ).annotate(
            age_group=Case(
                *[When(customer__age__gt=age_bins[i], customer__age__lte=age_bins[i+1],
                       then=Value(age_labels[i]))
                  for i in range(len(age_bins)-1)],
                default=Value('Unknown'),
                output_field=CharField(),
            )
        ).values('age_group').annotate(
            order_count=Count('id')
        ).order_by('-order_count').first()

        # Detailed demographics table
        detailed_demographics = []
        for age_label in age_labels:
            age_data = {
                'age_group': age_label,
                'total_customers': 0,
                'male_customers': 0,
                'female_customers': 0,
                'total_sales': 0,
                'avg_order_value': 0
            }

            # Get customer counts
            customer_counts = customers.filter(
                age_group=age_label
            ).values('gender').annotate(
                count=Count('id')
            )

            for count in customer_counts:
                age_data['total_customers'] += count['count']
                if count['gender'] == 'M':
                    age_data['male_customers'] = count['count']
                elif count['gender'] == 'F':
                    age_data['female_customers'] = count['count']

            # Get sales data
            sales_data = Order.objects.filter(
                status='completed',
                customer__age_group=age_label
            ).aggregate(
                total_sales=Sum('total_amount'),
                avg_order=Avg('total_amount')
            )

            age_data['total_sales'] = float(sales_data['total_sales'] or 0)
            age_data['avg_order_value'] = float(sales_data['avg_order'] or 0)

            detailed_demographics.append(age_data)

        return Response({
            'age_distribution': {
                'labels': age_labels,
                'values': [item['count'] for item in age_distribution]
            },
            'gender_distribution': gender_distribution,
            'gender_age_distribution': gender_age_data,
            'age_sales': {
                'age_groups': age_labels,
                'sales': [float(item['total_sales']) for item in age_sales]
            },
            'gender_age_sales': sales_by_gender_age,
            'average_age': avg_age or 0,
            'gender_ratio': gender_ratio,
            'most_active_age_group': most_active['age_group'] if most_active else 'Unknown',
            'detailed_demographics': detailed_demographics
        })

    @action(detail=False, methods=['GET'])
    def sales_trend(self, request):
        """Get sales trend analysis data"""
        period = request.query_params.get('period', 'monthly')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        category = request.query_params.get('category', 'all')

        # Build MongoDB aggregation pipeline
        pipeline = [{'$match': {'status': 'completed'}}]  # Changed from 'Delivered' to 'completed'

        if date_from and date_to:
            pipeline[0]['$match']['order_date'] = {
                '$gte': timezone.datetime.strptime(date_from, '%Y-%m-%d'),
                '$lte': timezone.datetime.strptime(date_to + ' 23:59:59', '%Y-%m-%d %H:%M:%S')
            }

        # Add category filter if specified
        if category != 'all':
            pipeline.extend([
                {'$unwind': '$items'},
                {'$lookup': {
                    'from': 'products',
                    'localField': 'items.product',
                    'foreignField': '_id',
                    'as': 'product_info'
                }},
                {'$unwind': '$product_info'},
                {'$match': {
                    'product_info.category': category
                }},
                {'$group': {
                    '_id': '$_id',
                    'order_date': {'$first': '$order_date'},
                    'total_amount': {'$first': '$total_amount'}
                }}
            ])

        # Group by time period
        if period == 'daily':
            group_id = {
                'year': {'$year': '$order_date'},
                'month': {'$month': '$order_date'},
                'day': {'$dayOfMonth': '$order_date'}
            }
        elif period == 'weekly':
            group_id = {
                'year': {'$year': '$order_date'},
                'week': {'$week': '$order_date'}
            }
        elif period == 'monthly':
            group_id = {
                'year': {'$year': '$order_date'},
                'month': {'$month': '$order_date'}
            }
        elif period == 'quarterly':
            group_id = {
                'year': {'$year': '$order_date'},
                'quarter': {'$ceil': {'$divide': [{'$month': '$order_date'}, 3]}}
            }
        else:  # yearly
            group_id = {'year': {'$year': '$order_date'}}

        # Add grouping stage
        pipeline.extend([
            {
                '$group': {
                    '_id': group_id,
                    'total_sales': {'$sum': '$total_amount'},
                    'order_count': {'$sum': 1}
                }
            },
            {'$sort': {'_id': 1}}
        ])

        # Execute aggregation
        sales_data = list(Order.objects.aggregate(*pipeline))

        # Format periods and calculate growth rates
        formatted_data = []
        prev_sales = None

        for item in sales_data:
            time_id = item['_id']
            
            # Format period label
            if period == 'daily':
                period_label = f"{time_id['year']}-{time_id['month']:02d}-{time_id['day']:02d}"
            elif period == 'weekly':
                period_label = f"{time_id['year']} Week {time_id['week']}"
            elif period == 'monthly':
                period_label = f"{time_id['year']}-{time_id['month']:02d}"
            elif period == 'quarterly':
                period_label = f"{time_id['year']} Q{time_id['quarter']}"
            else:  # yearly
                period_label = str(time_id['year'])

            # Calculate growth rate
            curr_sales = float(item['total_sales'])
            growth_rate = 0 if prev_sales is None else ((curr_sales - prev_sales) / prev_sales * 100)
            prev_sales = curr_sales

            formatted_data.append({
                'period': period_label,
                'total_sales': curr_sales,
                'order_count': item['order_count'],
                'growth_rate': round(growth_rate, 2)
            })

        # Get category distribution if not filtered by category
        if category == 'all':
            category_pipeline = [
                {'$match': pipeline[0]['$match']},
                {'$unwind': '$items'},
                {'$lookup': {
                    'from': 'products',
                    'localField': 'items.product',
                    'foreignField': '_id',
                    'as': 'product_info'
                }},
                {'$unwind': '$product_info'},
                {'$group': {
                    '_id': '$product_info.category',
                    'total_sales': {'$sum': '$total_amount'}
                }}
            ]
            
            category_data = {
                item['_id']: float(item['total_sales'])
                for item in Order.objects.aggregate(*category_pipeline)
                if item['_id']  # Filter out null categories
            }

            # Add category data to the response
            for item in formatted_data:
                item['category_sales'] = category_data

        # Get regional distribution
        region_pipeline = [
            {'$match': pipeline[0]['$match']},
            {'$lookup': {
                'from': 'customers',
                'localField': 'customer',
                'foreignField': '_id',
                'as': 'customer_info'
            }},
            {'$unwind': '$customer_info'},
            {'$group': {
                '_id': '$customer_info.location.region',
                'total_sales': {'$sum': '$total_amount'}
            }}
        ]
        
        region_data = {
            item['_id']: float(item['total_sales'])
            for item in Order.objects.aggregate(*region_pipeline)
            if item['_id']  # Filter out null regions
        }

        # Add region data to the response
        for item in formatted_data:
            item['region_sales'] = region_data

        return Response(formatted_data)

    @action(detail=False, methods=['GET'])
    def geographical_insights(self, request):
        """Get geographical distribution analysis"""
        period = request.query_params.get('period', 'last-year')
        region = request.query_params.get('region', 'all')

        # Calculate date range based on period
        end_date = timezone.now()
        if period == 'last-month':
            start_date = end_date - timedelta(days=30)
        elif period == 'last-quarter':
            start_date = end_date - timedelta(days=90)
        elif period == 'last-year':
            start_date = end_date - timedelta(days=365)
        else:  # all-time
            start_date = None

        # Build match stage for MongoDB aggregation
        match_stage = {'status': 'completed'}
        if start_date:
            match_stage['order_date'] = {'$gte': start_date}
        if region != 'all':
            match_stage['customer__location__region'] = region

        pipeline = [
            {'$match': match_stage},
            {
                '$group': {
                    '_id': '$customer__location__region',
                    'total_sales': {'$sum': '$total_amount'},
                    'customer_count': {'$addToSet': '$customer'},
                    'order_count': {'$sum': 1}
                }
            }
        ]

        regional_data = list(Order.objects.aggregate(*pipeline))

        # Calculate additional metrics
        total_sales = sum(r['total_sales'] for r in regional_data)
        for region in regional_data:
            region['customer_count'] = len(region['customer_count'])
            region['average_order_value'] = region['total_sales'] / region['order_count']
            region['market_share'] = (region['total_sales'] / total_sales * 100) if total_sales else 0

        serializer = GeographicalInsightSerializer(regional_data, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['GET'])
    def customer_analytics(self, request):
        """Get customer behavior and demographics analysis"""
        pipeline = [
            {
                '$group': {
                    '_id': {
                        'age_group': '$age_group',
                        'gender': '$gender'
                    },
                    'total_customers': {'$sum': 1},
                    'total_sales': {'$sum': '$total_purchases'},
                    'purchase_count': {'$sum': '$purchase_count'}
                }
            }
        ]

        customer_data = list(Customer.objects.aggregate(*pipeline))

        # Calculate derived metrics
        for data in customer_data:
            data['average_order_value'] = (
                data['total_sales'] / data['purchase_count'] 
                if data['purchase_count'] else 0
            )
            data['purchase_frequency'] = (
                data['purchase_count'] / data['total_customers']
                if data['total_customers'] else 0
            )

        serializer = CustomerAnalyticsSerializer(customer_data, many=True)
        return Response(serializer.data)

class GeographicalInsightsView(APIView):
    def get(self, request):
        # Get query parameters
        period = request.GET.get('period', 'last-year')
        region = request.GET.get('region', 'all')
        
        # Calculate date range based on period
        end_date = timezone.now()
        if period == 'last-month':
            start_date = end_date - timedelta(days=30)
        elif period == 'last-quarter':
            start_date = end_date - timedelta(days=90)
        elif period == 'last-year':
            start_date = end_date - timedelta(days=365)
        else:  # all-time
            start_date = None

        # Get customers grouped by city using MongoDB aggregation
        customer_pipeline = [
            {
                '$group': {
                    '_id': '$city',
                    'customer_count': {'$sum': 1}
                }
            }
        ]
        
        if start_date:
            customer_pipeline.insert(0, {
                '$match': {
                    'registration_date': {'$gte': start_date}
                }
            })
        
        if region != 'all':
            customer_pipeline.insert(0, {
                '$match': {
                    'location.region': region
                }
            })
        
        customer_pipeline.append({'$sort': {'customer_count': -1}})
        
        # Get total revenue by city using MongoDB aggregation
        profit_pipeline = [
            {
                '$lookup': {
                    'from': 'customers',
                    'localField': 'customer',
                    'foreignField': '_id',
                    'as': 'customer_info'
                }
            },
            {'$unwind': '$customer_info'},
            {
                '$group': {
                    '_id': '$customer_info.city',
                    'total_price': {'$sum': '$total_amount'}
                }
            }
        ]
        
        if start_date:
            profit_pipeline.insert(0, {
                '$match': {
                    'order_date': {'$gte': start_date}
                }
            })
        
        if region != 'all':
            profit_pipeline.insert(0, {
                '$match': {
                    'customer_info.location.region': region
                }
            })
        
        profit_pipeline.append({'$sort': {'total_price': -1}})
        
        try:
            # Execute aggregations
            customer_by_city = list(Customer.objects.aggregate(*customer_pipeline))
            profit_by_city = list(Order.objects.aggregate(*profit_pipeline))
            
            # Prepare response data
            response_data = {
                'cityCustomers': {
                    'top': {
                        'labels': [city['_id'] for city in customer_by_city[:10] if city['_id']],
                        'data': [city['customer_count'] for city in customer_by_city[:10] if city['_id']]
                    },
                    'bottom': {
                        'labels': [city['_id'] for city in customer_by_city[-10:] if city['_id']],
                        'data': [city['customer_count'] for city in customer_by_city[-10:] if city['_id']]
                    }
                },
                'cityProfit': {
                    'profit': {
                        'labels': [city['_id'] for city in profit_by_city[:10] if city['_id']],
                        'data': [float(city['total_price']) for city in profit_by_city[:10] if city['_id']]
                    },
                    'loss': {
                        'labels': [city['_id'] for city in profit_by_city[-10:] if city['_id']],
                        'data': [float(city['total_price']) for city in profit_by_city[-10:] if city['_id']]
                    }
                }
            }
            
            return Response(response_data)
        except Exception as e:
            return Response({'error': str(e)}, status=500)

class RecentOrdersView(APIView):
    def get(self, request):
        try:
            # Get limit from query params, default to 5
            limit = int(request.GET.get('limit', 5))
            
            # Get recent orders
            recent_orders = Order.objects.order_by('-order_date')[:limit]
            
            # Format orders for response
            orders_data = []
            for order in recent_orders:
                customer_id = order.customer.customer_id if order.customer else "Unknown"
                orders_data.append({
                    'order_id': order.order_id,
                    'customer_id': customer_id,
                    'date': order.order_date,
                    'total': float(order.total_amount),
                    'status': order.status
                })
            
            return Response(orders_data)
        except Exception as e:
            return Response({'error': str(e)}, status=500)