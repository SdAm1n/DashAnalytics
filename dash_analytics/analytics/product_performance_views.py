from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from datetime import datetime, timedelta
from core.models import Sales, Product
from django.db.models import Sum, Avg, Count, F, ExpressionWrapper, FloatField
import json


@api_view(['GET'])
@permission_classes([IsAuthenticated])  # Use authentication in production
def product_performance_api(request):
    """
    API endpoint for product performance page
    Fetches product performance metrics from the database
    """
    import logging
    logger = logging.getLogger(__name__)

    # Get query parameters for filtering
    period = request.GET.get('period', '1y')
    category = request.GET.get('category', 'all')
    db_alias = request.session.get('active_db', 'low_review_score_db')

    logger.info(
        f"Product Performance API request - Period: {period}, Category: {category}, DB: {db_alias}")

    # Calculate date range based on period
    end_date = datetime.now()
    if period == '7d':
        start_date = end_date - timedelta(days=7)
    elif period == '30d':
        start_date = end_date - timedelta(days=30)
    elif period == '90d':
        start_date = end_date - timedelta(days=90)
    elif period == '1y':
        start_date = end_date - timedelta(days=365)
    else:
        # Default to last year if an unexpected value is received
        start_date = end_date - timedelta(days=365)
        logger.warning(
            f"Unexpected period value: {period}. Defaulting to last year.")

    # Base query for sales data
    sales_query = Sales.objects.using(db_alias)
    if start_date:
        sales_query = sales_query.filter(sale_date__gte=start_date)

    # Get list of product ids in filtered sales
    sales_list = list(sales_query)
    product_ids_in_sales = list(set([sale.product_id for sale in sales_list]))
    logger.debug(
        f"Found {len(product_ids_in_sales)} unique product IDs in sales")

    # Get corresponding Product objects
    products = Product.objects.using(db_alias).filter(
        product_id__in=product_ids_in_sales)
    logger.debug(f"Retrieved {len(products)} products from database")

    # Log all available categories for debugging
    all_categories_debug = list(
        set(p.category_name for p in products if p.category_name))
    logger.debug(
        f"Available categories before filtering: {all_categories_debug}")

    # If category is specified, filter by category
    if category and category != 'all':
        # Log before filtering
        logger.info(f"Filtering by category: '{category}'")
        before_count = len(products)

        # Improved case-insensitive comparison of category names
        products = [p for p in products if p.category_name and p.category_name.lower(
        ) == category.lower()]

        # Get the filtered product IDs
        product_ids_filtered = [str(p.product_id) for p in products]

        # Filter sales list by these product IDs
        sales_list = [s for s in sales_list if str(
            s.product_id) in product_ids_filtered]

        # Log after filtering
        logger.info(
            f"After filtering: {len(products)} products (from {before_count})")
        if len(products) == 0:
            logger.warning(
                f"No products found with category '{category}'. Available categories: {all_categories_debug}")

    # Dictionary to map product_id to product_name
    product_map = {str(p.product_id): {
        'name': p.product_name,
        'category': p.category_name
    } for p in products}

    # Calculate aggregates for each product
    product_aggregates = {}

    for sale in sales_list:
        product_id = sale.product_id
        if product_id not in product_aggregates:
            product_aggregates[product_id] = {
                'total_quantity': 0,
                'total_revenue': 0,
                'total_profit': 0,
                'count': 0
            }

        product_aggregates[product_id]['total_quantity'] += sale.quantity
        product_aggregates[product_id]['total_revenue'] += sale.revenue
        product_aggregates[product_id]['total_profit'] += sale.profit
        product_aggregates[product_id]['count'] += 1

    # Now calculate derived metrics
    for product_id, agg in product_aggregates.items():
        if agg['count'] > 0:
            agg['avg_revenue'] = agg['total_revenue'] / agg['count']
        else:
            agg['avg_revenue'] = 0

        if product_id in product_map:
            agg['name'] = product_map[product_id]['name']
            agg['category'] = product_map[product_id]['category']
        else:
            agg['name'] = f"Product {product_id}"
            agg['category'] = "Unknown"

    # Get top products by various metrics
    best_selling_by_revenue = sorted(
        product_aggregates.values(),
        key=lambda x: x['total_revenue'],
        reverse=True
    )

    highest_volume_products = sorted(
        product_aggregates.values(),
        key=lambda x: x['total_quantity'],
        reverse=True
    )

    top_by_avg_revenue = sorted(
        product_aggregates.values(),
        key=lambda x: x['avg_revenue'],
        reverse=True
    )

    # Get category performance by summing product metrics
    category_performance = {}

    for product_id, agg in product_aggregates.items():
        category = agg['category']
        if category not in category_performance:
            category_performance[category] = {
                'total_sales': 0,
                'total_quantity': 0,
                'total_profit': 0,
                'product_count': 0
            }

        category_performance[category]['total_sales'] += agg['total_revenue']
        category_performance[category]['total_quantity'] += agg['total_quantity']
        category_performance[category]['total_profit'] += agg['total_profit']
        category_performance[category]['product_count'] += 1

    # Format categories for chart display
    category_chart_data = [
        {
            'category': cat,
            'total_sales': data['total_sales'],
            'total_quantity': data['total_quantity'],
            'product_count': data['product_count']
        }
        for cat, data in category_performance.items()
    ]

    # Sort categories by total sales
    category_chart_data = sorted(
        category_chart_data, key=lambda x: x['total_sales'], reverse=True)

    # Prepare response data
    response_data = {
        # Top metrics
        'best_product': {
            'name': best_selling_by_revenue[0]['name'] if best_selling_by_revenue else "No data",
            'revenue': best_selling_by_revenue[0]['total_revenue'] if best_selling_by_revenue else 0,
        },
        'top_category': {
            'name': category_chart_data[0]['category'] if category_chart_data else "No data",
            'sales': category_chart_data[0]['total_sales'] if category_chart_data else 0,
            'market_share': 100  # Default if there's only one category
        },
        'top_volume': {
            'name': highest_volume_products[0]['name'] if highest_volume_products else "No data",
            'quantity': highest_volume_products[0]['total_quantity'] if highest_volume_products else 0,
            'percentage': 100  # Will be calculated below if we have data
        },

        # Chart data
        'best_selling': [
            {
                'name': item['name'],
                'revenue': item['total_revenue'],
                'quantity': item['total_quantity']
            }
            for item in best_selling_by_revenue[:10]  # Top 10
        ],
        'category_performance': category_chart_data,
        'volume_data': [
            {
                'name': item['name'],
                'quantity': item['total_quantity']
            }
            for item in highest_volume_products[:10]  # Top 10
        ],
        'avg_revenue': [
            {
                'name': item['name'],
                'avg_revenue': item['avg_revenue']
            }
            for item in top_by_avg_revenue[:10]  # Top 10
        ],

        # Detailed table
        'detailed_performance': [
            {
                'name': item['name'],
                'category': item['category'],
                'units_sold': item['total_quantity'],
                'revenue': item['total_revenue'],
                'avg_price': item['avg_revenue'],
                'trend': 0  # Placeholder for trend calculation
            }
            # Top 50
            for item in sorted(product_aggregates.values(), key=lambda x: x['total_revenue'], reverse=True)[:50]
        ],
    }

    # Calculate percentages for top metrics if we have data
    if highest_volume_products:
        total_volume = sum(item['total_quantity']
                           for item in product_aggregates.values())
        if total_volume > 0:
            response_data['top_volume']['percentage'] = round(
                (highest_volume_products[0]['total_quantity'] / total_volume) * 100, 1)

    if category_chart_data:
        total_category_sales = sum(item['total_sales']
                                   for item in category_chart_data)
        if total_category_sales > 0:
            response_data['top_category']['market_share'] = round(
                (category_chart_data[0]['total_sales'] / total_category_sales) * 100, 1)

    # Calculate trends for products
    product_trends = {}
    if start_date:
        mid_date = start_date + (end_date - start_date) / 2
        for product_id, item in product_aggregates.items():
            # Filter sales by time periods (before and after mid-date)
            recent_sales = []
            older_sales = []

            for s in sales_list:
                if s.product_id == product_id:
                    # Handle timezone-aware and naive datetime comparison
                    sale_date = s.sale_date
                    # If sale_date has tzinfo but mid_date doesn't, or vice versa
                    if hasattr(sale_date, 'tzinfo') and sale_date.tzinfo is not None:
                        # Convert sale_date to naive datetime for comparison
                        sale_date = sale_date.replace(tzinfo=None)

                    if sale_date >= mid_date:
                        recent_sales.append(s)
                    else:
                        older_sales.append(s)

            recent_quantity = sum(s.quantity for s in recent_sales)
            older_quantity = sum(s.quantity for s in older_sales)

            if older_quantity > 0:
                growth = ((recent_quantity - older_quantity) /
                          older_quantity) * 100
                product_trends[product_id] = round(growth, 1)
            else:
                # If no sales in the first half or division by zero
                product_trends[product_id] = 0 if recent_quantity == 0 else 100

    # Update trend values in detailed_performance
    for item in response_data['detailed_performance']:
        product_id = next((pid for pid, agg in product_aggregates.items()
                           if agg['name'] == item['name']), None)
        if product_id and product_id in product_trends:
            item['trend'] = product_trends[product_id]

    # Get available categories for the filter dropdown
    # Get all Product objects for retrieving all available categories
    all_products = Product.objects.using(db_alias)
    # Filter out None or empty categories and use set for uniqueness
    all_categories = list(
        set(p.category_name for p in all_products if p.category_name))
    # Sort alphabetically for better user experience
    response_data['available_categories'] = sorted(all_categories)

    import logging
    logger = logging.getLogger(__name__)
    logger.debug(
        f"Returning {len(all_categories)} categories for filter dropdown")
    logger.debug(f"Categories: {all_categories}")

    return Response(response_data)
