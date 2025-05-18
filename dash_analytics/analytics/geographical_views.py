"""
Geographical insights API views for showing sales distribution by city,
top and bottom cities by various metrics, and regional performance
from both high_review_score_db and low_review_score_db
"""
import pycountry
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import timedelta
from core.models import Customer, Order, Product
from .models import GeographicalInsights
import json

# Dictionary mapping city names to country codes
CITY_TO_COUNTRY = {
    'New York': 'US', 'Los Angeles': 'US', 'Chicago': 'US', 'Houston': 'US', 'Phoenix': 'US',
    'Philadelphia': 'US', 'San Antonio': 'US', 'San Diego': 'US', 'Dallas': 'US', 'San Jose': 'US',
    'London': 'GB', 'Birmingham': 'GB', 'Manchester': 'GB', 'Liverpool': 'GB', 'Glasgow': 'GB',
    'Paris': 'FR', 'Marseille': 'FR', 'Lyon': 'FR', 'Toulouse': 'FR', 'Nice': 'FR',
    'Berlin': 'DE', 'Hamburg': 'DE', 'Munich': 'DE', 'Cologne': 'DE', 'Frankfurt': 'DE',
    'Tokyo': 'JP', 'Osaka': 'JP', 'Yokohama': 'JP', 'Nagoya': 'JP', 'Sapporo': 'JP',
    'Beijing': 'CN', 'Shanghai': 'CN', 'Guangzhou': 'CN', 'Shenzhen': 'CN', 'Chongqing': 'CN',
    'Sydney': 'AU', 'Melbourne': 'AU', 'Brisbane': 'AU', 'Perth': 'AU', 'Adelaide': 'AU',
    'Toronto': 'CA', 'Montreal': 'CA', 'Vancouver': 'CA', 'Calgary': 'CA', 'Edmonton': 'CA',
    'Mumbai': 'IN', 'Delhi': 'IN', 'Bangalore': 'IN', 'Hyderabad': 'IN', 'Chennai': 'IN',
    'São Paulo': 'BR', 'Rio de Janeiro': 'BR', 'Brasília': 'BR', 'Salvador': 'BR', 'Fortaleza': 'BR',
    'Moscow': 'RU', 'Saint Petersburg': 'RU', 'Novosibirsk': 'RU', 'Yekaterinburg': 'RU', 'Kazan': 'RU',
    'Mexico City': 'MX', 'Guadalajara': 'MX', 'Monterrey': 'MX', 'Puebla': 'MX', 'Tijuana': 'MX',
    'Amsterdam': 'NL', 'Rotterdam': 'NL', 'The Hague': 'NL', 'Utrecht': 'NL', 'Eindhoven': 'NL',
}


class GeographicalView(APIView):
    """API endpoint for geographical insights data"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get geographical data from both databases"""
        try:
            # Get filter parameters
            period = request.GET.get('period', 'last-year')
            region = request.GET.get('region', 'all')

            print(
                f"Geographical data request - Period: {period}, Region: {region}")

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

            # Create match conditions for MongoDB queries
            date_match = {} if not start_date else {'order_date': {'$gte': start_date}}
            region_match = {} if region == 'all' else {'location.region': region}

            # Get data from a single database (high_review_score_db)
            # for customer counts to avoid duplicate counting in replicated data
            try:
                db_data = self._get_geographical_data(
                    'high_review_score_db', date_match, region_match, start_date, end_date)
                print("Successfully retrieved geographical data")
            except Exception as e:
                print(f"Error retrieving geographical data: {e}")
                # Create empty structure if query fails
                db_data = {
                    'cityCustomers': {
                        'top': {'labels': [], 'data': []},
                        'bottom': {'labels': [], 'data': []}
                    },
                    'cityProfit': {
                        'profit': {'labels': [], 'data': []},
                        'loss': {'labels': [], 'data': []}
                    },
                    'regions': []
                }

            # Use the data directly without combining
            # Generate world map data (country codes and sales figures)
            combined_data = db_data
            world_map_data = self._generate_world_map_data(combined_data)

            # Create response data with detailed information
            response_data = {
                'cityCustomers': combined_data['cityCustomers'],
                'cityProfit': combined_data['cityProfit'],
                'regions': combined_data['regions'],
                'mapData': world_map_data
            }

            # Log response data structure and check for empty data
            print(
                f"Response data structure: {', '.join(response_data.keys())}")

            # Log detailed information about profit/loss data
            if 'cityProfit' in response_data and response_data['cityProfit']:
                profit_data = response_data['cityProfit'].get('profit', {})
                loss_data = response_data['cityProfit'].get('loss', {})

                profit_labels = profit_data.get('labels', [])
                profit_values = profit_data.get('data', [])
                loss_labels = loss_data.get('labels', [])
                loss_values = loss_data.get('data', [])

                print(
                    f"Profit data: {len(profit_labels)} cities, {len(profit_values)} values")
                print(
                    f"Loss data: {len(loss_labels)} cities, {len(loss_values)} values")

                if profit_labels and profit_values:
                    print(
                        f"Sample profit data: {profit_labels[:3]} - {profit_values[:3]}")
                else:
                    print("No profit data available")

                if loss_labels and loss_values:
                    print(
                        f"Sample loss data: {loss_labels[:3]} - {loss_values[:3]}")
                else:
                    print("No loss data available")
            else:
                print("No cityProfit data in response")

            return Response(response_data)

        except Exception as e:
            print(f"Error in geographical data API: {str(e)}")
            return Response({
                'error': str(e),
                'cityCustomers': {
                    'top': {'labels': [], 'data': []},
                    'bottom': {'labels': [], 'data': []}
                },
                'cityProfit': {
                    'profit': {'labels': [], 'data': []},
                    'loss': {'labels': [], 'data': []}
                },
                'regions': [],
                'mapData': {}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _get_geographical_data(self, db_alias, date_match, region_match, start_date, end_date):
        """Get geographical data from specified database with filters applied"""
        try:
            # Customer data by city
            customer_pipeline = [
                {'$match': region_match}] if region_match else []
            customer_pipeline.extend([
                {'$group': {
                    '_id': '$city',
                    'customer_count': {'$sum': 1}
                }},
                {'$sort': {'customer_count': -1}}
            ])

            customer_by_city = list(Customer.objects.using(
                db_alias).aggregate(*customer_pipeline))

            # Get top 10 and bottom 10 cities by customer count
            top_customers = sorted([c for c in customer_by_city if c['_id']],
                                   key=lambda x: x['customer_count'], reverse=True)[:10]
            bottom_customers = sorted(
                [c for c in customer_by_city if c['_id']], key=lambda x: x['customer_count'])[:10]

            # Get profit by city - we need to calculate based on order and product data
            profit_pipeline = []
            if date_match and 'order_date' in date_match and date_match['order_date']:
                profit_pipeline.append({'$match': date_match})

            profit_pipeline.extend([
                # Join with customers collection to get city information
                {'$lookup': {
                    'from': 'customers',
                    'localField': 'customer_id',
                    'foreignField': '_id',
                    'as': 'customer_info'
                }},
                {'$unwind': '$customer_info'},

                # Join with products collection to get price information
                {'$lookup': {
                    'from': 'products',
                    'localField': 'product_id',
                    'foreignField': '_id',
                    'as': 'product_info'
                }},
                {'$unwind': '$product_info'},

                # Calculate profit per order (price * quantity)
                {'$addFields': {
                    'revenue': {'$multiply': ['$product_info.price', '$quantity']},
                    # Assume 40% profit margin
                    'cost': {'$multiply': [{'$multiply': ['$product_info.price', 0.6]}, '$quantity']}
                }},
                {'$addFields': {
                    # Calculate actual profit
                    'profit': {'$subtract': ['$revenue', '$cost']}
                }}
            ])

            # Apply region filter if provided
            if region_match and 'location.region' in region_match:
                profit_pipeline.append({
                    '$match': {'customer_info.location.region': region_match.get('location.region')}
                })

            # Add a stage to handle null cities
            profit_pipeline.append({
                '$match': {
                    'customer_info.city': {'$ne': None, '$ne': ''}
                }
            })

            # Group by city to get total profit/loss
            profit_pipeline.extend([
                {'$group': {
                    '_id': '$customer_info.city',
                    # Sum the calculated profit
                    'total_profit': {'$sum': '$profit'},
                    'total_revenue': {'$sum': '$revenue'},
                    'total_cost': {'$sum': '$cost'},
                    'order_count': {'$sum': 1}
                }},
                {'$sort': {'total_profit': -1}}
            ])

            # Execute the pipeline and get results
            pipeline_results = list(Order.objects.using(
                db_alias).aggregate(*profit_pipeline))
            print(
                f"Raw pipeline results for {db_alias}: {len(pipeline_results)} cities")

            # Filter out null or undefined city names and ensure profit values are numeric
            profit_by_city = []
            for p in pipeline_results:
                if not p['_id']:  # Skip items with no city
                    continue

                # Ensure profit values are numeric
                try:
                    p['total_profit'] = float(p['total_profit'])
                    p['total_revenue'] = float(p['total_revenue'])
                    p['total_cost'] = float(p['total_cost'])
                    profit_by_city.append(p)
                except (ValueError, TypeError) as e:
                    print(f"Skipping invalid profit data for {p['_id']}: {e}")

            print(
                f"Found {len(profit_by_city)} cities with valid profit/loss data in {db_alias}")

            # Get top profit and top loss cities
            # Ensure proper sorting by safely converting to float
            top_profit = []
            top_loss = []

            try:
                # First, ensure all values are valid
                processed_profit_data = []
                for p in profit_by_city:
                    if not p['_id']:  # Skip items with no city
                        continue

                    try:
                        # Use the calculated profit value
                        total_profit = float(p['total_profit'])
                        processed_profit_data.append({
                            '_id': p['_id'],
                            'total_price': total_profit,  # Keep field name for backward compatibility
                            'total_profit': total_profit,
                            'total_revenue': float(p['total_revenue']),
                            'total_cost': float(p['total_cost']),
                            'order_count': p['order_count']
                        })
                    except (ValueError, TypeError) as e:
                        print(
                            f"Error converting profit value for {p['_id']}: {e}")

                # Now separate into profit and loss based on the calculated profit
                profit_data = [
                    p for p in processed_profit_data if p['total_profit'] > 0]
                loss_data = [
                    p for p in processed_profit_data if p['total_profit'] < 0]

                # Sort profit data (highest profit first)
                top_profit = sorted(
                    profit_data, key=lambda x: x['total_price'], reverse=True)[:10]

                # Sort loss data (highest loss first - most negative values first)
                top_loss = sorted(
                    loss_data, key=lambda x: x['total_price'])[:10]

                print(
                    f"Found {len(top_profit)} profitable cities and {len(top_loss)} loss-making cities in {db_alias}")

            except (ValueError, TypeError) as e:
                print(f"Error sorting profit/loss data in {db_alias}: {e}")
                top_profit = []
                top_loss = []

            # Get sales growth by region
            region_pipeline = []
            if date_match and 'order_date' in date_match and date_match['order_date']:
                region_pipeline.append({'$match': date_match})

            region_pipeline.extend([
                {'$lookup': {
                    'from': 'customers',
                    'localField': 'customer',
                    'foreignField': '_id',
                    'as': 'customer_info'
                }},
                {'$unwind': '$customer_info'},
                {'$group': {
                    '_id': '$customer_info.location.region',
                    'current_sales': {'$sum': '$total_amount'},
                    'order_count': {'$sum': 1}
                }}
            ])

            # Get current period sales by region
            current_region_data = list(Order.objects.using(
                db_alias).aggregate(*region_pipeline))

            # Calculate previous period for comparison
            prev_start_date = None
            prev_end_date = None
            if start_date:
                current_period_days = (end_date - start_date).days
                prev_start_date = start_date - \
                    timedelta(days=current_period_days)
                prev_end_date = start_date

            # Get previous period sales
            prev_region_data = []
            if prev_start_date:
                prev_match = {'order_date': {
                    '$gte': prev_start_date, '$lt': prev_end_date}}
                prev_pipeline = [{'$match': prev_match}]
                prev_pipeline.extend([
                    {'$lookup': {
                        'from': 'customers',
                        'localField': 'customer',
                        'foreignField': '_id',
                        'as': 'customer_info'
                    }},
                    {'$unwind': '$customer_info'},
                    {'$group': {
                        '_id': '$customer_info.location.region',
                        'previous_sales': {'$sum': '$total_amount'}
                    }}
                ])
                prev_region_data = list(Order.objects.using(
                    db_alias).aggregate(*prev_pipeline))

            # Combine current and previous data to calculate growth
            region_data = []
            total_current_sales = sum(r['current_sales']
                                      for r in current_region_data)

            # Create a lookup dictionary for previous sales
            prev_sales_lookup = {r['_id']: r['previous_sales']
                                 for r in prev_region_data}

            for region_item in current_region_data:
                if not region_item['_id']:  # Skip if region is None or empty
                    continue

                region_name = region_item['_id']
                current_sales = region_item['current_sales']
                previous_sales = prev_sales_lookup.get(region_name, 0)

                # Calculate growth percentage
                growth_pct = 0
                if previous_sales > 0:
                    growth_pct = (
                        (current_sales - previous_sales) / previous_sales) * 100

                # Calculate market share
                market_share = (current_sales / total_current_sales *
                                100) if total_current_sales > 0 else 0

                region_data.append({
                    'region': region_name,
                    'currentSales': f"${float(current_sales):,.2f}",
                    'previousSales': f"${float(previous_sales):,.2f}",
                    'growth': f"{'+' if growth_pct >= 0 else ''}{growth_pct:.1f}%",
                    'marketShare': f"{market_share:.1f}%"
                })

            return {
                'cityCustomers': {
                    'top': {
                        'labels': [city['_id'] for city in top_customers if city['_id']],
                        'data': [city['customer_count'] for city in top_customers if city['_id']]
                    },
                    'bottom': {
                        'labels': [city['_id'] for city in bottom_customers if city['_id']],
                        'data': [city['customer_count'] for city in bottom_customers if city['_id']]
                    }
                },
                'cityProfit': {
                    'profit': {
                        'labels': [city['_id'] for city in top_profit if city['_id']],
                        'data': [float(city['total_profit']) for city in top_profit if city['_id']]
                    },
                    'loss': {
                        'labels': [city['_id'] for city in top_loss if city['_id']],
                        # Make loss values positive for the frontend
                        'data': [-float(city['total_profit']) for city in top_loss if city['_id']]
                    }
                },
                'regions': region_data
            }
        except Exception as e:
            print(f"Error fetching geographical data from {db_alias}: {e}")
            # Return an empty data structure on error
            return {
                'cityCustomers': {
                    'top': {'labels': [], 'data': []},
                    'bottom': {'labels': [], 'data': []}
                },
                'cityProfit': {
                    'profit': {'labels': [], 'data': []},
                    'loss': {'labels': [], 'data': []}
                },
                'regions': []
            }

    def _combine_geographical_data(self, low_db_data, high_db_data):
        """Combine data from both databases"""
        # Combine city customers data
        combined_top_customers = self._combine_city_data(
            low_db_data['cityCustomers']['top']['labels'],
            low_db_data['cityCustomers']['top']['data'],
            high_db_data['cityCustomers']['top']['labels'],
            high_db_data['cityCustomers']['top']['data']
        )

        combined_bottom_customers = self._combine_city_data(
            low_db_data['cityCustomers']['bottom']['labels'],
            low_db_data['cityCustomers']['bottom']['data'],
            high_db_data['cityCustomers']['bottom']['labels'],
            high_db_data['cityCustomers']['bottom']['data']
        )

        # Sort combined data
        combined_top_customers = sorted(
            combined_top_customers, key=lambda x: x[1], reverse=True)[:10]
        combined_bottom_customers = sorted(
            combined_bottom_customers, key=lambda x: x[1])[:10]

        # Combine city profit data with proper handling for empty datasets
        # Make sure we have valid data structures before attempting to combine
        low_profit_labels = low_db_data['cityProfit']['profit'].get(
            'labels', []) if low_db_data['cityProfit']['profit'] else []
        low_profit_data = low_db_data['cityProfit']['profit'].get(
            'data', []) if low_db_data['cityProfit']['profit'] else []
        high_profit_labels = high_db_data['cityProfit']['profit'].get(
            'labels', []) if high_db_data['cityProfit']['profit'] else []
        high_profit_data = high_db_data['cityProfit']['profit'].get(
            'data', []) if high_db_data['cityProfit']['profit'] else []

        combined_profit = self._combine_city_data(
            low_profit_labels,
            low_profit_data,
            high_profit_labels,
            high_profit_data
        )

        # Similar handling for loss data
        low_loss_labels = low_db_data['cityProfit']['loss'].get(
            'labels', []) if low_db_data['cityProfit']['loss'] else []
        low_loss_data = low_db_data['cityProfit']['loss'].get(
            'data', []) if low_db_data['cityProfit']['loss'] else []
        high_loss_labels = high_db_data['cityProfit']['loss'].get(
            'labels', []) if high_db_data['cityProfit']['loss'] else []
        high_loss_data = high_db_data['cityProfit']['loss'].get(
            'data', []) if high_db_data['cityProfit']['loss'] else []

        combined_loss = self._combine_city_data(
            low_loss_labels,
            low_loss_data,
            high_loss_labels,
            high_loss_data
        )

        # Sort combined profit/loss data with safer conversion
        combined_profit_sorted = []
        if combined_profit:
            try:
                # For profit data, make sure values are positive for proper sorting
                combined_profit_sorted = sorted(
                    [(city, abs(float(value)))
                     for city, value in combined_profit if city],
                    key=lambda x: x[1],
                    reverse=True
                )[:10]
                print(
                    f"Combined profit data: {len(combined_profit_sorted)} cities")
                for i, (city, value) in enumerate(combined_profit_sorted[:3]):
                    print(f"  Top profit {i+1}: {city} = ${value:.2f}")
            except Exception as e:
                print(f"Error sorting combined profit data: {e}")
                combined_profit_sorted = []

        combined_loss_sorted = []
        if combined_loss:
            try:
                # For loss data, we want the most negative values first (biggest losses)
                # Convert to negative absolute values for chart display
                combined_loss_sorted = sorted(
                    [(city, -abs(float(value)))
                     for city, value in combined_loss if city],
                    key=lambda x: x[1]
                )[:10]
                print(
                    f"Combined loss data: {len(combined_loss_sorted)} cities")
                for i, (city, value) in enumerate(combined_loss_sorted[:3]):
                    print(f"  Top loss {i+1}: {city} = ${value:.2f}")
            except Exception as e:
                print(f"Error sorting combined loss data: {e}")
                combined_loss_sorted = []

        # Use the sorted data
        combined_profit = combined_profit_sorted
        combined_loss = combined_loss_sorted

        # Combine regions data
        region_dict = {}

        # Check if we have regions data
        low_db_regions = low_db_data.get('regions', [])
        high_db_regions = high_db_data.get('regions', [])

        # If both regions are empty, create a sample region to avoid empty table
        if not low_db_regions and not high_db_regions:
            # Add a default region with zero values to make the table work
            combined_regions = [{
                'region': 'No data available',
                'currentSales': '$0.00',
                'previousSales': '$0.00',
                'growth': '0.0%',
                'marketShare': '100.0%'
            }]

            return {
                'cityCustomers': {
                    'top': {
                        'labels': [city[0] for city in combined_top_customers],
                        'data': [city[1] for city in combined_top_customers]
                    },
                    'bottom': {
                        'labels': [city[0] for city in combined_bottom_customers],
                        'data': [city[1] for city in combined_bottom_customers]
                    }
                },
                'cityProfit': {
                    'profit': {
                        'labels': [city[0] for city in combined_profit],
                        'data': [city[1] for city in combined_profit]
                    },
                    'loss': {
                        'labels': [city[0] for city in combined_loss],
                        'data': [city[1] for city in combined_loss]
                    }
                },
                'regions': combined_regions
            }

        # Process low_db regions
        for region in low_db_regions:
            region_dict[region['region']] = {
                'currentSales': float(region['currentSales'].replace('$', '').replace(',', '')),
                'previousSales': float(region['previousSales'].replace('$', '').replace(',', '')),
                'growth': float(region['growth'].replace('+', '').replace('%', '')),
                'marketShare': float(region['marketShare'].replace('%', ''))
            }

        # Add or update with high_db regions
        for region in high_db_regions:
            region_name = region['region']
            if region_name in region_dict:
                # Add values for existing regions
                region_dict[region_name]['currentSales'] += float(
                    region['currentSales'].replace('$', '').replace(',', ''))
                region_dict[region_name]['previousSales'] += float(
                    region['previousSales'].replace('$', '').replace(',', ''))

                # Recalculate growth
                current = region_dict[region_name]['currentSales']
                previous = region_dict[region_name]['previousSales']
                growth = 0
                if previous > 0:
                    growth = ((current - previous) / previous) * 100
                elif current > 0:
                    growth = 100
                region_dict[region_name]['growth'] = growth
            else:
                # Add new region
                region_dict[region_name] = {
                    'currentSales': float(region['currentSales'].replace('$', '').replace(',', '')),
                    'previousSales': float(region['previousSales'].replace('$', '').replace(',', '')),
                    'growth': float(region['growth'].replace('+', '').replace('%', '')),
                    'marketShare': float(region['marketShare'].replace('%', ''))
                }

        # Calculate total sales for market share
        total_sales = sum(r['currentSales'] for r in region_dict.values())

        # Format regions data
        combined_regions = []
        for region_name, data in region_dict.items():
            # Recalculate market share
            market_share = (data['currentSales'] /
                            total_sales * 100) if total_sales > 0 else 0

            combined_regions.append({
                'region': region_name,
                'currentSales': f"${data['currentSales']:,.2f}",
                'previousSales': f"${data['previousSales']:,.2f}",
                'growth': f"{'+' if data['growth'] >= 0 else ''}{data['growth']:.1f}%",
                'marketShare': f"{market_share:.1f}%"
            })

        # Sort by current sales
        combined_regions = sorted(
            combined_regions,
            key=lambda x: float(x['currentSales'].replace(
                '$', '').replace(',', '')),
            reverse=True
        )

        return {
            'cityCustomers': {
                'top': {
                    'labels': [city[0] for city in combined_top_customers],
                    'data': [city[1] for city in combined_top_customers]
                },
                'bottom': {
                    'labels': [city[0] for city in combined_bottom_customers],
                    'data': [city[1] for city in combined_bottom_customers]
                }
            },
            'cityProfit': {
                'profit': {
                    'labels': [city[0] for city in combined_profit],
                    'data': [city[1] for city in combined_profit]
                },
                'loss': {
                    'labels': [city[0] for city in combined_loss],
                    'data': [city[1] for city in combined_loss]
                }
            },
            'regions': combined_regions
        }

    def _combine_city_data(self, labels1, data1, labels2, data2):
        """Helper function to combine city data from two sources"""
        combined_data = {}

        # Ensure we have valid lists
        labels1 = labels1 or []
        data1 = data1 or []
        labels2 = labels2 or []
        data2 = data2 or []

        # Add data from first source
        for i, label in enumerate(labels1):
            # Make sure we don't go out of bounds and have a valid label
            if i < len(data1) and label:
                try:
                    if label in combined_data:
                        combined_data[label] += float(data1[i]
                                                      ) if data1[i] is not None else 0
                    else:
                        combined_data[label] = float(
                            data1[i]) if data1[i] is not None else 0
                except (ValueError, TypeError) as e:
                    print(
                        f"Error processing data for {label} from source 1: {e}")

        # Add data from second source
        for i, label in enumerate(labels2):
            # Make sure we don't go out of bounds and have a valid label
            if i < len(data2) and label:
                try:
                    if label in combined_data:
                        combined_data[label] += float(data2[i]
                                                      ) if data2[i] is not None else 0
                    else:
                        combined_data[label] = float(
                            data2[i]) if data2[i] is not None else 0
                except (ValueError, TypeError) as e:
                    print(
                        f"Error processing data for {label} from source 2: {e}")

        # Convert to list of tuples for easier sorting
        # Always keep profit/loss values as floats to preserve precision
        result = []
        for city, value in combined_data.items():
            if city:  # Ensure we have a valid city name
                try:
                    # For customer counts, use integers. For profit/loss, keep as floats
                    if isinstance(value, int):
                        result.append((city, value))
                    else:
                        result.append((city, float(value)))
                except (ValueError, TypeError):
                    # Skip invalid values
                    pass

        return result

    def _generate_world_map_data(self, combined_data):
        """Generate world map data by mapping cities to countries"""
        country_sales = {}
        # Add city data for more meaningful map visualization
        city_data = {}

        # Validate profit data exists
        if 'profit' in combined_data['cityProfit'] and 'labels' in combined_data['cityProfit']['profit']:
            profit_labels = combined_data['cityProfit']['profit']['labels']
            profit_data = combined_data['cityProfit']['profit']['data']

            # Process profit data safely
            for i, city in enumerate(profit_labels):
                if i < len(profit_data) and city in CITY_TO_COUNTRY:
                    country_code = CITY_TO_COUNTRY[city]
                    try:
                        sales_amount = float(profit_data[i])

                        # Add to country sales
                        if country_code in country_sales:
                            country_sales[country_code] += sales_amount
                        else:
                            country_sales[country_code] = sales_amount

                        # Add city data for potential markers
                        city_data[city] = {
                            'sales': sales_amount,
                            'type': 'profit'
                        }
                    except (ValueError, TypeError) as e:
                        print(f"Error processing profit data for {city}: {e}")

        # Validate loss data exists
        if 'loss' in combined_data['cityProfit'] and 'labels' in combined_data['cityProfit']['loss']:
            loss_labels = combined_data['cityProfit']['loss']['labels']
            loss_data = combined_data['cityProfit']['loss']['data']

            # Process loss data safely
            for i, city in enumerate(loss_labels):
                if i < len(loss_data) and city in CITY_TO_COUNTRY:
                    country_code = CITY_TO_COUNTRY[city]
                    try:
                        # Loss data may already be negative, but we'll ensure it is
                        sales_amount = float(loss_data[i])

                        if country_code in country_sales:
                            country_sales[country_code] += sales_amount
                        else:
                            country_sales[country_code] = sales_amount

                        # Add city data for potential markers
                        city_data[city] = {
                            'sales': sales_amount,
                            'type': 'loss'
                        }
                    except (ValueError, TypeError) as e:
                        print(f"Error processing loss data for {city}: {e}")

        # Add data from customer counts if profit/loss data is insufficient
        if not country_sales and 'top' in combined_data['cityCustomers']:
            for i, city in enumerate(combined_data['cityCustomers']['top']['labels']):
                if i < len(combined_data['cityCustomers']['top']['data']) and city in CITY_TO_COUNTRY:
                    country_code = CITY_TO_COUNTRY[city]
                    customer_count = combined_data['cityCustomers']['top']['data'][i]

                    # We'll use customer count as a proxy for sales if no other data
                    if country_code in country_sales:
                        country_sales[country_code] += customer_count
                    else:
                        country_sales[country_code] = customer_count

        # Ensure we have at least some data if empty
        if not country_sales:
            # Add default data for US to avoid empty maps
            country_sales['US'] = 0

        return country_sales

    def _format_prediction(self, prediction):
        """Format prediction data for API response"""
        return {
            'id': str(prediction.id),
            'prediction_type': prediction.prediction_type,
            'prediction_period': prediction.prediction_period,
            'prediction_data': json.loads(prediction.prediction_data)
        }
