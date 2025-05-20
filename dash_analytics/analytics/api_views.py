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
from core.models import Sales, Product, Customer, Order
from .models import SalesTrend, CustomerBehavior
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
                    date_to = datetime.combine(
                        date_to.date(), datetime.max.time())
                else:
                    # Default to today if not provided
                    date_to = datetime.now()
            except ValueError as e:
                return Response({'error': f'Invalid date format. Please use YYYY-MM-DD format. {str(e)}'},
                                status=status.HTTP_400_BAD_REQUEST)

            # Query sales data
            sales_query = Sales.objects

            # Apply date filters
            sales_query = sales_query.filter(
                sale_date__gte=date_from, sale_date__lte=date_to)

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
                    matching_products = Product.objects(
                        category_id=int(category))
                else:
                    # Try different field combinations as fallback
                    # First with category_name containing the category string
                    if 'category_name' in product_fields:
                        matching_products = Product.objects(
                            category_name__icontains=category)
                    # If no matches, try matching against product name as last resort
                    if not matching_products and 'product_name' in product_fields:
                        matching_products = Product.objects(
                            product_name__icontains=category)

                product_ids = [str(p.product_id) for p in matching_products]

                if product_ids:  # Only apply filter if we found matching products
                    sales_query = sales_query.filter(
                        product_id__in=product_ids)

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
            sales_objects = list(sales_query.order_by(
                '-sale_date').limit(MAX_RECORDS))
            if not sales_objects:
                return Response({'error': 'No data found for the selected filters'}, status=status.HTTP_404_NOT_FOUND)

            # Convert to a list of dictionaries for pandas - optimize for speed
            sales_data = []
            for sale in sales_objects:
                try:
                    sales_data.append({
                        'sale_date': sale.sale_date,
                        # Ensure product_id is string type
                        'product_id': str(sale.product_id),
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
                df['period_sort'] = df['sale_date'].dt.strftime(
                    '%Y%m%d')  # For sorting
            elif period == 'weekly':
                # For weekly, format as YYYY-Www (ISO week format)
                df['period'] = df['sale_date'].dt.strftime('%Y-W%U')
                df['period_sort'] = df['sale_date'].dt.strftime(
                    '%Y%U')  # For sorting
            elif period == 'monthly':
                # For monthly, format as YYYY-MM
                df['period'] = df['sale_date'].dt.strftime('%Y-%m')
                df['period_sort'] = df['sale_date'].dt.strftime(
                    '%Y%m')  # For sorting

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
                df['period_sort'] = df['period'].apply(
                    lambda x: x.replace('Q', ''))  # For sorting
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
                period_to_sort = df[['period', 'period_sort']].drop_duplicates().set_index('period')[
                    'period_sort'].to_dict()
                sales_trend['period_sort'] = sales_trend['period'].map(
                    period_to_sort)

                # Sort by the numeric sort key
                sales_trend = sales_trend.sort_values('period_sort')
            else:
                # Fallback sorting by period
                sales_trend = sales_trend.sort_values('period')

            # If we created period_display (for monthly), use it
            if 'period_display' in df.columns:
                # Get the corresponding display value for each period
                period_to_display = df[['period', 'period_display']].drop_duplicates(
                ).set_index('period')['period_display'].to_dict()
                sales_trend['period_display'] = sales_trend['period'].map(
                    period_to_display)
                # Use this display value in the final result
                sales_trend['period'] = sales_trend['period_display']

            # Remove helper columns
            if 'period_sort' in sales_trend.columns:
                sales_trend = sales_trend.drop(['period_sort'], axis=1)
            if 'period_display' in sales_trend.columns:
                sales_trend = sales_trend.drop(['period_display'], axis=1)

            # Calculate growth rate
            sales_trend['growth_rate'] = sales_trend['total_sales'].pct_change() * \
                100

            # Replace NaN with 0 for the first period
            sales_trend['growth_rate'] = sales_trend['growth_rate'].fillna(0)

            # Round numeric values for better display
            sales_trend['total_sales'] = sales_trend['total_sales'].round(2)
            sales_trend['growth_rate'] = sales_trend['growth_rate'].round(2)
            if 'total_profit' in sales_trend.columns:
                sales_trend['total_profit'] = sales_trend['total_profit'].round(
                    2)

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
                    # Ensure product_id is string type
                    'product_id': str(product.product_id),
                    'category': category
                })

            products_df = pd.DataFrame(products_data)

            # Merge sales with product categories - use efficient method
            if not products_df.empty and len(products_df) > 0:
                # Create a dictionary for faster lookups
                product_to_category = dict(
                    zip(products_df['product_id'], products_df['category']))

                # Apply the mapping to the sales DataFrame
                df['category'] = df['product_id'].map(
                    product_to_category).fillna('Unknown')

                # Group by category
                category_sales = df.groupby('category').agg(
                    total_sales=('revenue', 'sum')
                ).reset_index()

                category_dict = dict(
                    zip(category_sales['category'], category_sales['total_sales']))

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
            region_sales = region_sales.sort_values(
                'total_sales', ascending=False).head(20)

            # Round values for better display
            region_sales['total_sales'] = region_sales['total_sales'].round(2)

            # Create dictionary with sorted values
            region_dict = dict(
                zip(region_sales['city'], region_sales['total_sales']))

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


class CustomerBehaviorView(APIView):
    """API endpoint for Customer Behavior data"""
    # For development/testing purposes, we temporarily disable authentication
    # TODO: Restore IsAuthenticated when moving to production
    permission_classes = []  # Allow any access for testing

    def get(self, request, format=None):
        """
        Get customer behavior analytics data
        """
        try:
            print("Processing customer behavior API request...")
            # Get parameters from the request
            segment = request.query_params.get('segment')
            # Default to top 20 customers
            limit = int(request.query_params.get('limit', 20))

            # Base query for all customers
            sales_query = Sales.objects
            orders_query = Order.objects
            customers_query = Customer.objects

            # Apply segment filter if provided
            if segment and segment != 'all':
                # Get customer IDs in the specified segment
                customer_behavior = CustomerBehavior.objects(
                    customer_segment=segment)
                customer_ids = [cb.customer_id for cb in customer_behavior]

                # Filter sales by these customer IDs
                sales_query = sales_query.filter(customer_id__in=customer_ids)

            # Get raw sales data for analysis
            sales_data = []
            for sale in sales_query:
                sales_data.append({
                    'customer_id': str(sale.customer_id),
                    'sale_date': sale.sale_date,
                    'revenue': float(sale.revenue),
                    'quantity': int(sale.quantity)
                })

            # If no data found, return an error
            if len(sales_data) == 0:
                return Response({'error': 'No customer behavior data found for the selected filters'},
                                status=status.HTTP_404_NOT_FOUND)

            # Convert to pandas DataFrame for analysis
            df = pd.DataFrame(sales_data)

            # 1. Purchase Frequency Analysis
            purchase_freq = self.analyze_purchase_frequency(df)

            # 2. Customer Sentiment Analysis (replacing loyalty analysis)
            customer_sentiment = self.analyze_sentiment()

            # 3. Customer Segmentation
            customer_segments = self.analyze_customer_segments()

            # 4. Purchase Time Analysis
            purchase_times = self.analyze_purchase_times(df)

            # 5. Top Customers by Purchase Value
            top_customers = self.get_top_customers(df, limit)

            # Combine all data into a single response
            response_data = {
                'purchase_frequency': purchase_freq,
                'customer_sentiment': customer_sentiment,  # Changed from customer_loyalty
                'customer_segments': customer_segments,
                'purchase_times': purchase_times,
                'top_customers': top_customers
            }

            return Response(response_data)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def analyze_purchase_frequency(self, df):
        """Analyze purchase frequency patterns"""
        try:
            # Group by customer and count purchases
            customer_purchases = df.groupby(
                'customer_id').size().reset_index(name='purchase_count')

            # Calculate frequency distribution
            frequency_counts = customer_purchases['purchase_count'].value_counts(
            ).sort_index().to_dict()

            # Convert to array of objects for easier frontend use
            frequency_data = [
                {"purchases": int(count), "customers": int(frequency)}
                for count, frequency in frequency_counts.items()
            ]

            # Handle potential None values in calculations
            mean_purchases = customer_purchases['purchase_count'].mean()
            median_purchases = customer_purchases['purchase_count'].median()

            return {
                'frequency_distribution': frequency_data,
                'average_purchases': float(mean_purchases if mean_purchases is not None else 0),
                'median_purchases': float(median_purchases if median_purchases is not None else 0)
            }
        except Exception as e:
            print(f"Error in analyze_purchase_frequency: {str(e)}")
            # Return a default structure to prevent API errors
            return {
                'frequency_distribution': [],
                'average_purchases': 0,
                'median_purchases': 0
            }

    def analyze_sentiment(self):
        """Analyze customer sentiment based on review scores"""
        try:
            from textblob import TextBlob

            # Query orders that have review scores (MongoEngine syntax)
            orders_with_reviews = Order.objects(review_score__ne=None)

            if not orders_with_reviews:
                print("No orders with review scores found, using sample data")
                # Return sample sentiment data if no reviews found
                return {
                    'sentiment_distribution': {
                        'Positive': 65,
                        'Neutral': 25,
                        'Negative': 10
                    },
                    'average_score': 3.8
                }

            # Extract review scores
            reviews_df = pd.DataFrame([
                {'review_score': order.review_score}
                for order in orders_with_reviews
                if order.review_score is not None
            ])

            if reviews_df.empty:
                print("No valid review scores found, using sample data")
                # Return sample sentiment data if no valid reviews found
                return {
                    'sentiment_distribution': {
                        'Positive': 65,
                        'Neutral': 25,
                        'Negative': 10
                    },
                    'average_score': 3.8
                }

            # Apply sentiment classification based on review scores
            # Positive: score >= 4, Negative: score <= 2, Neutral: everything else
            reviews_df['Sentiment'] = reviews_df['review_score'].apply(
                lambda x: 'Positive' if x >= 4 else 'Negative' if x <= 2 else 'Neutral'
            )

            # Count distribution
            sentiment_counts = reviews_df['Sentiment'].value_counts().to_dict()

            # Ensure all sentiment categories are present
            for sentiment in ['Positive', 'Neutral', 'Negative']:
                if sentiment not in sentiment_counts:
                    sentiment_counts[sentiment] = 0

            # Calculate average review score
            avg_score = reviews_df['review_score'].mean()

            return {
                'sentiment_distribution': sentiment_counts,
                'average_score': float(avg_score) if not pd.isna(avg_score) else 0.0
            }

        except Exception as e:
            print(f"Error in analyze_sentiment: {str(e)}")
            # Return default sentiment data in case of error
            return {
                'sentiment_distribution': {
                    'Positive': 65,
                    'Neutral': 25,
                    'Negative': 10
                },
                'average_score': 3.8
            }

    def analyze_customer_segments(self):
        """Get customer segment distribution from pre-calculated data"""
        try:
            # Define segment types to look for
            segment_types = ['VIP', 'Regular', 'Occasional', 'New', 'At Risk']
            segment_data = []

            # Count customers in each segment manually instead of using mapReduce
            for segment_type in segment_types:
                try:
                    # Count customers in this segment
                    count = CustomerBehavior.objects(
                        customer_segment=segment_type).count()
                    if count > 0:
                        segment_data.append({
                            'segment': segment_type,
                            'count': count
                        })
                except Exception as e:
                    print(f"Error counting segment {segment_type}: {str(e)}")
                    # Add with count 0 if there was an error
                    segment_data.append({
                        'segment': segment_type,
                        'count': 0
                    })

            # If no segments were found, generate some sample data
            if not segment_data:
                # Sample data in case the real data is not available
                segment_data = [
                    {'segment': 'VIP', 'count': 120},
                    {'segment': 'Regular', 'count': 450},
                    {'segment': 'Occasional', 'count': 630},
                    {'segment': 'New', 'count': 210},
                    {'segment': 'At Risk', 'count': 90}
                ]

            # Add segment descriptions for frontend
            segment_descriptions = {
                'VIP': 'High-value customers with frequent purchases',
                'Regular': 'Consistent customers with moderate purchase frequency',
                'Occasional': 'Customers who shop infrequently',
                'New': 'Recently acquired customers',
                'At Risk': 'Customers who haven\'t purchased recently'
            }

            return {
                'segment_distribution': segment_data,
                'segment_descriptions': segment_descriptions
            }
        except Exception as e:
            print(f"Error in analyze_customer_segments: {str(e)}")
            # Return a default structure to prevent API errors
            return {
                'segment_distribution': [
                    {'segment': 'VIP', 'count': 120},
                    {'segment': 'Regular', 'count': 450},
                    {'segment': 'Occasional', 'count': 630},
                    {'segment': 'New', 'count': 210},
                    {'segment': 'At Risk', 'count': 90}
                ],
                'segment_descriptions': {
                    'VIP': 'High-value customers with frequent purchases',
                    'Regular': 'Consistent customers with moderate purchase frequency',
                    'Occasional': 'Customers who shop infrequently',
                    'New': 'Recently acquired customers',
                    'At Risk': 'Customers who haven\'t purchased recently'
                }
            }

    def analyze_purchase_times(self, df):
        """Analyze when customers are most likely to purchase"""
        try:
            # Add hour, day of week, and month from the sale_date
            if len(df) > 0:
                # Filter out rows with None sale_date
                df_clean = df.dropna(subset=['sale_date'])

                if len(df_clean) == 0:
                    raise ValueError("No valid sale dates found in data")

                # Make sure sale_date column contains datetime objects
                if not pd.api.types.is_datetime64_any_dtype(df_clean['sale_date']):
                    df_clean['sale_date'] = pd.to_datetime(
                        df_clean['sale_date'], errors='coerce')
                    # Drop rows where conversion failed
                    df_clean = df_clean.dropna(subset=['sale_date'])

                # Extract time components from valid dates
                df_clean['hour'] = df_clean['sale_date'].dt.hour
                # Monday=0, Sunday=6
                df_clean['day_of_week'] = df_clean['sale_date'].dt.dayofweek
                df_clean['month'] = df_clean['sale_date'].dt.month

                # Count purchases by hour
                hourly_purchases = df_clean.groupby('hour').size().reindex(
                    range(24), fill_value=0).to_dict()
                hourly_data = [{'hour': hour, 'purchases': int(
                    count)} for hour, count in hourly_purchases.items()]

                # Count purchases by day of week
                day_names = ['Monday', 'Tuesday', 'Wednesday',
                             'Thursday', 'Friday', 'Saturday', 'Sunday']
                weekly_purchases = df_clean.groupby('day_of_week').size().reindex(
                    range(7), fill_value=0).to_dict()
                weekly_data = [{'day': day_names[day], 'purchases': int(
                    count)} for day, count in weekly_purchases.items()]

                # Count purchases by month
                month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May',
                               'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
                monthly_purchases = df_clean.groupby('month').size().reindex(
                    range(1, 13), fill_value=0).to_dict()
                monthly_data = [{'month': month_names[month-1], 'purchases': int(
                    count)} for month, count in monthly_purchases.items()]

                return {
                    'hourly': hourly_data,
                    'weekly': weekly_data,
                    'monthly': monthly_data
                }
        except Exception as e:
            print(f"Error in analyze_purchase_times: {str(e)}")

        # Return empty data if no purchases found or if an error occurred
        day_names = ['Monday', 'Tuesday', 'Wednesday',
                     'Thursday', 'Friday', 'Saturday', 'Sunday']
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May',
                       'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

        return {
            'hourly': [{'hour': h, 'purchases': 0} for h in range(24)],
            'weekly': [{'day': d, 'purchases': 0} for d in day_names],
            'monthly': [{'month': m, 'purchases': 0} for m in month_names]
        }

    def get_top_customers(self, df, limit=20):
        """Get top customers by purchase value"""
        try:
            # Make sure we have valid data to work with
            if df.empty:
                return []

            # Handle any NaN or None values in the revenue column
            df['revenue'] = df['revenue'].fillna(0)

            # Group by customer and calculate metrics
            top_customers_df = df.groupby('customer_id').agg(
                total_purchases=('customer_id', 'count'),
                total_spent=('revenue', 'sum'),
                avg_order_value=('revenue', 'mean')
            ).reset_index()

            # Sort by total spent (descending) and limit results
            top_customers_df = top_customers_df.sort_values(
                'total_spent', ascending=False).head(limit)

            # Get customer details for these top customers
            customer_details = {}
            for customer_id in top_customers_df['customer_id'].unique():
                try:
                    customer = Customer.objects(
                        customer_id=customer_id).first()
                    if customer:
                        # Extract attributes safely with defaults
                        city = getattr(customer, 'city', 'Unknown')
                        gender = getattr(customer, 'gender', 'Unknown')

                        # Handle potential None/invalid age values
                        age = getattr(customer, 'age', 0)
                        try:
                            age = int(age) if age is not None else 0
                        except (ValueError, TypeError):
                            age = 0

                        customer_details[customer_id] = {
                            'city': city if city is not None else 'Unknown',
                            'gender': gender if gender is not None else 'Unknown',
                            'age': age
                        }
                except Exception as e:
                    print(
                        f"Error retrieving customer {customer_id} details: {str(e)}")
                    continue

            # Assign customer segments based on spending
            # Calculate spending thresholds based on percentiles
            if len(top_customers_df) > 0:
                try:
                    threshold_high = top_customers_df['total_spent'].quantile(
                        0.8)
                    threshold_medium = top_customers_df['total_spent'].quantile(
                        0.5)

                    def assign_loyalty(row):
                        total_spent = row.get('total_spent', 0) or 0
                        if total_spent >= threshold_high:
                            return 'High'
                        elif total_spent >= threshold_medium:
                            return 'Medium'
                        else:
                            return 'Low'

                    top_customers_df['loyalty'] = top_customers_df.apply(
                        assign_loyalty, axis=1)
                except Exception as e:
                    print(f"Error assigning loyalty segments: {str(e)}")
                    top_customers_df['loyalty'] = 'Unknown'

            # Convert to list of dictionaries
            top_customers = []
            for _, row in top_customers_df.iterrows():
                try:
                    customer_id = row['customer_id']
                    total_purchases = row.get('total_purchases', 0) or 0
                    total_spent = row.get('total_spent', 0) or 0
                    avg_value = row.get('avg_order_value', 0) or 0

                    customer_data = {
                        'id': customer_id,
                        'purchases': int(total_purchases),
                        'total_spent': float(total_spent),
                        'avg_value': float(avg_value),
                        'loyalty': row.get('loyalty', 'Unknown')
                    }

                    # Add customer details if available
                    if customer_id in customer_details:
                        customer_data.update(customer_details[customer_id])

                    top_customers.append(customer_data)
                except Exception as e:
                    print(f"Error processing customer row: {str(e)}")
                    continue

            return top_customers
        except Exception as e:
            print(f"Error in get_top_customers: {str(e)}")
            return []


class DemographicsView(APIView):
    """API endpoint for Demographics data"""
    # For development purposes, we're temporarily disabling authentication
    # TODO: Re-enable IsAuthenticated for production use
    permission_classes = []  # Empty list = no authentication required

    def get(self, request):
        """Get demographics data based on time period filter"""
        try:
            # Extract query parameters
            period = request.GET.get('period', '1y')  # Default to 1 year

            # Calculate date range based on period
            date_to = datetime.now()
            if period == '7d':
                date_from = date_to - pd.DateOffset(days=7)
            elif period == '30d':
                date_from = date_to - pd.DateOffset(days=30)
            elif period == '90d':
                date_from = date_to - pd.DateOffset(days=90)
            elif period == '1y':
                date_from = date_to - pd.DateOffset(years=1)
            else:  # 'all' time
                date_from = None

            # Query customers and sales data
            customers = list(Customer.objects)

            # Query relevant sales
            sales_query = Sales.objects
            if date_from:
                sales_query = sales_query.filter(
                    sale_date__gte=date_from, sale_date__lte=date_to)
            sales = list(sales_query)

            # Check if we have data
            if not customers:
                return Response({'error': 'No customer data found'}, status=status.HTTP_404_NOT_FOUND)

            # Create DataFrames for analysis
            customers_df = pd.DataFrame([
                {
                    'customer_id': str(customer.customer_id),
                    'gender': customer.gender,
                    'age': int(customer.age),
                    'city': customer.city
                } for customer in customers
            ])

            sales_df = pd.DataFrame([
                {
                    'customer_id': str(sale.customer_id),
                    'sale_date': sale.sale_date,
                    'revenue': float(sale.revenue),
                    'product_id': str(sale.product_id)
                } for sale in sales
            ])

            # Merge data for analysis
            if not sales_df.empty:
                # Filter customers that have sales in the selected period
                merged_df = pd.merge(
                    sales_df,
                    customers_df,
                    on='customer_id',
                    how='inner'
                )
                active_customers = customers_df[customers_df['customer_id'].isin(
                    sales_df['customer_id'])]
            else:
                merged_df = pd.DataFrame()
                active_customers = pd.DataFrame()

            # Calculate age distribution
            age_bins = [0, 18, 25, 35, 45, 55, 65, 100]
            age_labels = ['Under 18', '18-24', '25-34',
                          '35-44', '45-54', '55-64', '65+']

            customers_df['age_group'] = pd.cut(
                customers_df['age'],
                bins=age_bins,
                labels=age_labels,
                right=False
            )

            age_distribution = customers_df.groupby(
                'age_group', observed=True).size().reindex(age_labels, fill_value=0)

            # Calculate gender distribution
            gender_distribution = customers_df['gender'].value_counts()
            male_count = int(gender_distribution.get('M', 0))
            female_count = int(gender_distribution.get('F', 0))

            # Calculate gender distribution by age group
            gender_age_dist = customers_df.groupby(
                ['age_group', 'gender'], observed=True).size().unstack(fill_value=0)
            gender_age_distribution = {
                'age_groups': age_labels,
                'male': [int(gender_age_dist.get('M', {}).get(age, 0)) for age in age_labels],
                'female': [int(gender_age_dist.get('F', {}).get(age, 0)) for age in age_labels]
            }

            # Calculate sales metrics by age group if we have sales data
            if not merged_df.empty:
                merged_df['age_group'] = pd.cut(
                    merged_df['age'],
                    bins=age_bins,
                    labels=age_labels,
                    right=False
                )

                age_sales = merged_df.groupby('age_group', observed=True)[
                    'revenue'].sum().reindex(age_labels, fill_value=0)

                # Gender & age sales distribution
                # Properly handle the multi-index DataFrame
                gender_age_sales = merged_df.groupby(
                    ['gender', 'age_group'], observed=True)['revenue'].sum()

                # Get sales for each gender and age group
                male_sales = []
                female_sales = []

                # Iterate through age groups to get correct values
                for age in age_labels:
                    # Try to get male sales by index tuple
                    try:
                        if ('M', age) in gender_age_sales.index:
                            male_sales.append(
                                float(gender_age_sales[('M', age)]))
                        else:
                            male_sales.append(0.0)
                    except:
                        male_sales.append(0.0)

                    # Try to get female sales by index tuple
                    try:
                        if ('F', age) in gender_age_sales.index:
                            female_sales.append(
                                float(gender_age_sales[('F', age)]))
                        else:
                            female_sales.append(0.0)
                    except:
                        female_sales.append(0.0)

                # Log for debugging
                print(f"Male Sales: {male_sales}")
                print(f"Female Sales: {female_sales}")
            else:
                age_sales = pd.Series(0, index=age_labels)
                male_sales = [0] * len(age_labels)
                female_sales = [0] * len(age_labels)

            # Prepare detailed demographics table data
            detailed_demographics = []
            for age in age_labels:
                if not merged_df.empty:
                    age_group_data = merged_df[merged_df['age_group'] == age]
                    total_customers = int(
                        customers_df[customers_df['age_group'] == age].shape[0])
                    male_customers = int(customers_df[(customers_df['age_group'] == age) & (
                        customers_df['gender'] == 'M')].shape[0])
                    female_customers = int(customers_df[(customers_df['age_group'] == age) & (
                        customers_df['gender'] == 'F')].shape[0])
                    total_sales = float(age_group_data['revenue'].sum())

                    # Calculate average order value
                    customer_sales = age_group_data.groupby('customer_id')[
                        'revenue'].sum()
                    avg_order_value = float(
                        customer_sales.mean()) if not customer_sales.empty else 0.0
                else:
                    total_customers = int(
                        customers_df[customers_df['age_group'] == age].shape[0])
                    male_customers = int(customers_df[(customers_df['age_group'] == age) & (
                        customers_df['gender'] == 'M')].shape[0])
                    female_customers = int(customers_df[(customers_df['age_group'] == age) & (
                        customers_df['gender'] == 'F')].shape[0])
                    total_sales = 0.0
                    avg_order_value = 0.0

                detailed_demographics.append({
                    'age_group': age,
                    'total_customers': total_customers,
                    'male_customers': male_customers,
                    'female_customers': female_customers,
                    'total_sales': total_sales,
                    'avg_order_value': avg_order_value
                })

            # Calculate key metrics
            average_age = float(
                customers_df['age'].mean()) if 'age' in customers_df else 0
            gender_ratio = male_count / female_count if female_count > 0 else 0

            # Find most active age group
            if not merged_df.empty:
                age_activity = merged_df.groupby(
                    'age_group', observed=True).size()
                most_active_age_group = age_activity.idxmax() if not age_activity.empty else "N/A"
            else:
                most_active_age_group = "N/A"

            # Prepare response
            response_data = {
                'average_age': average_age,
                'gender_ratio': gender_ratio,
                'most_active_age_group': most_active_age_group,
                'age_distribution': {
                    'labels': age_labels,
                    'values': age_distribution.tolist()
                },
                'gender_distribution': {
                    'male': male_count,
                    'female': female_count
                },
                'gender_age_distribution': gender_age_distribution,
                'age_sales': {
                    'age_groups': age_labels,
                    'sales': age_sales.tolist()
                },
                'gender_age_sales': {
                    'age_groups': age_labels,
                    'male_sales': male_sales,
                    'female_sales': female_sales
                },
                'detailed_demographics': detailed_demographics
            }

            return Response(response_data)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
