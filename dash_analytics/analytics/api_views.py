"""
API views for the analytics module
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.permissions import IsAuthenticated
from datetime import datetime
import pandas as pd
import numpy as np
from core.models import Sales, Product
from .models import SalesTrend
from django.db.models import Sum, Avg, Count, F


class SalesTrendView(APIView):
    """API endpoint for Sales Trend data"""
    # Authentication is restored for production use
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get sales trend data based on filters"""
        try:
            # Extract query parameters
            period = request.GET.get('period', 'monthly')
            category = request.GET.get('category', 'all')
            date_from = request.GET.get('date_from')
            date_to = request.GET.get('date_to')

            # Parse dates
            try:
                if date_from:
                    date_from = datetime.strptime(date_from, '%Y-%m-%d')
                else:
                    # Default to 6 months ago if not provided
                    date_from = datetime.now() - pd.DateOffset(months=6)
                    
                if date_to:
                    date_to = datetime.strptime(date_to, '%Y-%m-%d')
                    # Add time to make it inclusive of the entire day
                    date_to = datetime.combine(date_to.date(), datetime.max.time())
                else:
                    # Default to today if not provided
                    date_to = datetime.now()
            except ValueError as e:
                return Response({'error': f'Invalid date format. Please use YYYY-MM-DD format. {str(e)}'}, 
                               status=status.HTTP_400_BAD_REQUEST)

            # Query sales data
            sales_query = Sales.objects
            
            # Apply date filters
            sales_query = sales_query.filter(sale_date__gte=date_from, sale_date__lte=date_to)
                
            # Apply category filter
            if category and category != 'all':
                # Join with products to filter by category
                # Using MongoDB/mongoengine compatible query
                # Get correct field from product based on what's available
                matching_products = []
                
                # Get a sample product to check available fields
                sample_product = Product.objects.first()
                product_fields = sample_product._fields.keys() if sample_product else []
                
                if 'category' in product_fields:
                    matching_products = Product.objects(category=category)
                elif 'category_name' in product_fields:
                    matching_products = Product.objects(category_name=category)
                elif 'category_id' in product_fields and category.isdigit():
                    # Only try to filter by category_id if the category is numeric
                    matching_products = Product.objects(category_id=int(category))
                else:
                    # Try different field combinations as fallback
                    # First with category_name containing the category string
                    if 'category_name' in product_fields:
                        matching_products = Product.objects(category_name__icontains=category)
                    # If no matches, try matching against product name as last resort
                    if not matching_products and 'product_name' in product_fields:
                        matching_products = Product.objects(product_name__icontains=category)
                
                product_ids = [str(p.product_id) for p in matching_products]
                
                if product_ids:  # Only apply filter if we found matching products
                    sales_query = sales_query.filter(product_id__in=product_ids)
                
            # Count results before fetching to optimize query
            count = sales_query.count()
            if count == 0:
                return Response({'error': 'No data found for the selected filters'}, status=status.HTTP_404_NOT_FOUND)
            
            # For very large datasets, consider adding pagination
            # This prevents memory issues when fetching millions of records
            MAX_RECORDS = 50000  # Arbitrary limit for safety
            
            if count > MAX_RECORDS:
                # For extremely large datasets, consider aggregation pipeline
                # This would be a more advanced implementation
                # For now we'll add a warning in the response
                warning_message = f"Large dataset detected ({count} records). Results may be slower than usual."
                print(warning_message)  # Log the warning
                
            # Get raw data from MongoDB and convert to a list for pandas
            # We use .limit() as a safeguard against extremely large datasets
            sales_objects = list(sales_query.order_by('-sale_date').limit(MAX_RECORDS))
            if not sales_objects:
                return Response({'error': 'No data found for the selected filters'}, status=status.HTTP_404_NOT_FOUND)
            
            # Convert to a list of dictionaries for pandas - optimize for speed
            sales_data = []
            for sale in sales_objects:
                try:
                    sales_data.append({
                        'sale_date': sale.sale_date,
                        'product_id': str(sale.product_id),  # Ensure product_id is string type
                        'revenue': float(sale.revenue),
                        'profit': float(sale.profit) if hasattr(sale, 'profit') else 0.0,
                        'quantity': int(sale.quantity) if hasattr(sale, 'quantity') else 0,
                        'city': sale.city if hasattr(sale, 'city') else None
                    })
                except (ValueError, TypeError, AttributeError) as e:
                    # Skip records with data type issues instead of failing the entire request
                    print(f"Error processing sale record: {str(e)}")
                
            df = pd.DataFrame(sales_data)
            
            # Convert sale_date to datetime if it's not
            if not pd.api.types.is_datetime64_any_dtype(df['sale_date']):
                df['sale_date'] = pd.to_datetime(df['sale_date'])
            
            # Group by period with proper formatting and sorting
            if period == 'daily':
                # For daily, format as YYYY-MM-DD
                df['period'] = df['sale_date'].dt.strftime('%Y-%m-%d')
                df['period_sort'] = df['sale_date'].dt.strftime('%Y%m%d')  # For sorting
            elif period == 'weekly':
                # For weekly, format as YYYY-Www (ISO week format)
                df['period'] = df['sale_date'].dt.strftime('%Y-W%U')
                df['period_sort'] = df['sale_date'].dt.strftime('%Y%U')  # For sorting
            elif period == 'monthly':
                # For monthly, format as YYYY-MM
                df['period'] = df['sale_date'].dt.strftime('%Y-%m')
                df['period_sort'] = df['sale_date'].dt.strftime('%Y%m')  # For sorting
                
                # Add month names for user-friendly display
                month_names = {
                    '01': 'Jan', '02': 'Feb', '03': 'Mar', '04': 'Apr', 
                    '05': 'May', '06': 'Jun', '07': 'Jul', '08': 'Aug',
                    '09': 'Sep', '10': 'Oct', '11': 'Nov', '12': 'Dec'
                }
                
                # Extract month from period and replace with name
                df['period_display'] = df['period'].apply(
                    lambda x: f"{x.split('-')[0]}-{month_names.get(x.split('-')[1], x.split('-')[1])}"
                )
            elif period == 'quarterly':
                # For quarterly, format as YYYY-QN
                df['period'] = df['sale_date'].dt.to_period('Q').astype(str)
                df['period_sort'] = df['period'].apply(lambda x: x.replace('Q', ''))  # For sorting
            else:  # yearly
                # For yearly, format as YYYY
                df['period'] = df['sale_date'].dt.strftime('%Y')
                df['period_sort'] = df['period']  # For sorting
            
            # Get sales trend data with aggregations
            sales_trend = df.groupby('period').agg(
                total_sales=('revenue', 'sum'),
                order_count=('product_id', 'count'),
                total_profit=('profit', 'sum'),
                total_quantity=('quantity', 'sum')
            ).reset_index()
            
            # Add period_sort if available
            if 'period_sort' in df.columns:
                # Get the corresponding period_sort for each period
                period_to_sort = df[['period', 'period_sort']].drop_duplicates().set_index('period')['period_sort'].to_dict()
                sales_trend['period_sort'] = sales_trend['period'].map(period_to_sort)
                
                # Sort by the numeric sort key
                sales_trend = sales_trend.sort_values('period_sort')
            else:
                # Fallback sorting by period
                sales_trend = sales_trend.sort_values('period')
            
            # If we created period_display (for monthly), use it
            if 'period_display' in df.columns:
                # Get the corresponding display value for each period
                period_to_display = df[['period', 'period_display']].drop_duplicates().set_index('period')['period_display'].to_dict()
                sales_trend['period_display'] = sales_trend['period'].map(period_to_display)
                # Use this display value in the final result
                sales_trend['period'] = sales_trend['period_display']
            
            # Remove helper columns
            if 'period_sort' in sales_trend.columns:
                sales_trend = sales_trend.drop(['period_sort'], axis=1)
            if 'period_display' in sales_trend.columns:
                sales_trend = sales_trend.drop(['period_display'], axis=1)
            
            # Calculate growth rate
            sales_trend['growth_rate'] = sales_trend['total_sales'].pct_change() * 100
            
            # Replace NaN with 0 for the first period
            sales_trend['growth_rate'] = sales_trend['growth_rate'].fillna(0)
            
            # Round numeric values for better display
            sales_trend['total_sales'] = sales_trend['total_sales'].round(2)
            sales_trend['growth_rate'] = sales_trend['growth_rate'].round(2)
            if 'total_profit' in sales_trend.columns:
                sales_trend['total_profit'] = sales_trend['total_profit'].round(2)
            
            # Get unique product IDs from sales data for more efficient category lookup
            unique_product_ids = df['product_id'].unique()
            
            # Only query products that appear in the filtered sales data
            products_query = Product.objects(product_id__in=unique_product_ids)
            
            # Prepare products data
            products_data = []
            
            # Get a sample product to determine which field to use for category
            sample_product = Product.objects.first() if products_query.count() > 0 else None
            category_field = None
            
            if sample_product:
                if hasattr(sample_product, 'category'):
                    category_field = 'category'
                elif hasattr(sample_product, 'category_name'):
                    category_field = 'category_name'
            
            for product in products_query:
                category = 'Unknown'
                if category_field:
                    category = getattr(product, category_field, 'Unknown')
                elif hasattr(product, 'category_id'):
                    # Try to use category_id as fallback
                    category = f"Category {product.category_id}"
                    
                products_data.append({
                    'product_id': str(product.product_id),  # Ensure product_id is string type
                    'category': category
                })
            
            products_df = pd.DataFrame(products_data)
            
            # Merge sales with product categories - use efficient method
            if not products_df.empty and len(products_df) > 0:
                # Create a dictionary for faster lookups
                product_to_category = dict(zip(products_df['product_id'], products_df['category']))
                
                # Apply the mapping to the sales DataFrame
                df['category'] = df['product_id'].map(product_to_category).fillna('Unknown')
                
                # Group by category 
                category_sales = df.groupby('category').agg(
                    total_sales=('revenue', 'sum')
                ).reset_index()
                
                category_dict = dict(zip(category_sales['category'], category_sales['total_sales']))
                
                # Sort categories by sales value (descending)
                category_dict = {k: v for k, v in sorted(
                    category_dict.items(), 
                    key=lambda item: item[1], 
                    reverse=True
                )}
            else:
                category_dict = {}
                
            # Get sales by region (city)
            region_sales = df.groupby('city').agg(
                total_sales=('revenue', 'sum')
            ).reset_index()
            
            # Sort regions by sales and limit to top 20 to avoid overwhelming the chart
            region_sales = region_sales.sort_values('total_sales', ascending=False).head(20)
            
            # Round values for better display
            region_sales['total_sales'] = region_sales['total_sales'].round(2)
            
            # Create dictionary with sorted values
            region_dict = dict(zip(region_sales['city'], region_sales['total_sales']))
            
            # Prepare response
            result = sales_trend.to_dict(orient='records')
            
            # Add category and region data to the first record (if result is not empty)
            if result:
                result[0]['category_sales'] = category_dict
                result[0]['region_sales'] = region_dict
                
                # Add metadata about the query
                result[0]['metadata'] = {
                    'total_records': len(sales_data),
                    'period_type': period,
                    'date_range': {
                        'from': date_from.strftime('%Y-%m-%d'),
                        'to': date_to.strftime('%Y-%m-%d')
                    },
                    'filters_applied': {
                        'category': category if category != 'all' else None
                    }
                }
            
            return Response(result)
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
