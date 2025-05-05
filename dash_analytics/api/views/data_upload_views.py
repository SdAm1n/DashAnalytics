import logging
import pandas as pd
from decimal import Decimal
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from core.models import Customer, Product, Order, Sales, RawDataUpload
from analytics.models import (
    SalesTrend, ProductPerformance, CategoryPerformance,
    Demographics, GeographicalInsights, CustomerBehavior, Review, Prediction
)
from django.core.files.uploadedfile import UploadedFile
import json

logger = logging.getLogger(__name__)

class DataUploadView(APIView):
    def post(self, request):
        try:
            if 'file' not in request.FILES:
                return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

            file = request.FILES['file']
            if not isinstance(file, UploadedFile):
                return Response({'error': 'Invalid file format'}, status=status.HTTP_400_BAD_REQUEST)

            if not file.name.endswith('.csv'):
                return Response({'error': 'File must be a CSV'}, status=status.HTTP_400_BAD_REQUEST)

            # Check for duplicate file
            existing_upload = RawDataUpload.objects(file_name=file.name).first()
            if existing_upload:
                return Response({
                    'error': f'A file with name "{file.name}" has already been uploaded on {existing_upload.upload_date.strftime("%Y-%m-%d %H:%M:%S")}',
                    'details': {
                        'upload_date': existing_upload.upload_date,
                        'file_name': existing_upload.file_name
                    }
                }, status=status.HTTP_409_CONFLICT)

            # Create upload record
            upload = RawDataUpload(
                file_name=file.name,
                status='processing'
            ).save()

            try:
                # Read CSV file
                df = pd.read_csv(file)
                
                # Set total records count
                upload.total_records = len(df)
                upload.save()
                
                # Process data and store in respective collections
                for index, row in df.iterrows():
                    try:
                        # Create or update customer
                        customer_data = {
                            'customer_id': row['customer_id'],
                            'gender': row['gender'],
                            'age': row['age'],
                            'city': row['city']
                        }
                        Customer.objects(customer_id=row['customer_id']).update_one(
                            upsert=True, **customer_data)

                        # Create or update product
                        product_data = {
                            'product_id': row['product_id'],
                            'product_name': row['product_name'],
                            'category_id': row['category_id'],
                            'category_name': row['category_name'],
                            'price': float(row['price'])
                        }
                        Product.objects(product_id=row['product_id']).update_one(
                            upsert=True, **product_data)

                        # Create new order
                        try:
                            customer = Customer.objects(customer_id=int(row['customer_id'])).first()
                            product = Product.objects(product_id=int(row['product_id'])).first()
                            
                            if not customer:
                                logger.error(f"Customer not found for ID: {row['customer_id']}")
                                continue
                                
                            if not product:
                                logger.error(f"Product not found for ID: {row['product_id']}")
                                continue

                            # Generate a unique order_id since it's not in the CSV
                            order_date = pd.to_datetime(row['order_date'])
                            generated_order_id = f"ORD-{customer.customer_id}-{product.product_id}-{order_date.strftime('%Y%m%d%H%M%S')}"

                            order_data = {
                                'order_id': generated_order_id,
                                'order_date': order_date,
                                'customer_id': customer,
                                'product_id': product,
                                'quantity': int(row['quantity']),
                                'payment_method': row.get('payment_method', 'Cash'),  # Default to Cash if not provided
                                'review_score': float(row['review_score']) if pd.notna(row.get('review_score')) else None
                            }
                            
                            # Try to find existing order first (unlikely since we generate unique IDs)
                            existing_order = Order.objects(order_id=generated_order_id).first()
                            if existing_order:
                                # Update existing order
                                for key, value in order_data.items():
                                    setattr(existing_order, key, value)
                                existing_order.save()
                                logger.info(f"Updated existing order: {generated_order_id}")
                            else:
                                # Create new order
                                new_order = Order(**order_data)
                                new_order.save()
                                logger.info(f"Created new order: {generated_order_id}")

                            # Create sales record with matching ID
                            sales_data = {
                                'id': f"SALE-{generated_order_id}",
                                'customer_id': str(row['customer_id']),
                                'product_id': str(row['product_id']),
                                'quantity': int(row['quantity']),
                                'sale_date': order_date,
                                'revenue': float(row['quantity'] * row['price']),
                                'profit': float(row['quantity'] * row['price'] * 0.3),  # 30% profit margin
                                'city': row['city']
                            }
                            Sales(**sales_data).save()

                            # Create review record if review score exists
                            if pd.notna(row.get('review_score')):
                                review_data = {
                                    'id': f"REV-{generated_order_id}",
                                    'customer_id': str(row['customer_id']),
                                    'product_id': str(row['product_id']),
                                    'review_score': float(row['review_score']),
                                    'sentiment': self.get_sentiment(float(row['review_score']))
                                }
                                Review(**review_data).save()

                            upload.processed_records += 1
                            upload.save()
                            
                        except Exception as e:
                            logger.error(f"Error creating order for row {index}: {str(e)}")
                            continue

                    except Exception as row_error:
                        logger.error(f"Error processing row {index}: {str(row_error)}")
                        continue

                # Update upload status
                upload.status = 'completed'
                upload.save()

                # Trigger analytics calculations
                self.update_analytics()

                return Response({
                    'message': 'Data uploaded and processed successfully',
                    'successful_records': upload.processed_records
                })

            except Exception as process_error:
                upload.status = 'failed'
                upload.error_message = str(process_error)
                upload.save()
                raise process_error

        except Exception as e:
            logger.error(f"Error processing data upload: {str(e)}")
            return Response(
                {'error': 'Error processing upload: ' + str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def get(self, request):
        """
        List all previous uploads
        """
        try:
            uploads = RawDataUpload.objects.all().order_by('-upload_date')
            result = []
            for upload in uploads:
                result.append({
                    'id': str(upload.id),
                    'file_name': upload.file_name,
                    'upload_date': upload.upload_date,
                    'status': upload.status,
                    'file_size': 0,  # Placeholder since we don't store file size
                    'row_count': upload.processed_records,
                    'processed': upload.status == 'completed'
                })
            return Response(result)
        except Exception as e:
            logger.error(f"Error fetching uploads: {str(e)}")
            return Response(
                {'error': 'Error fetching uploads: ' + str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def update_analytics(self):
        """Update all analytics collections based on current data"""
        try:
            # MongoDB is already connected through settings.py, just verify connection
            from mongoengine.connection import get_db
            try:
                db = get_db()
                logger.info("MongoDB connection verified")
            except Exception as conn_err:
                logger.error(f"MongoDB connection error: {str(conn_err)}")
                raise

            # Clear existing analytics data
            try:
                collections_to_clear = [
                    SalesTrend, ProductPerformance, CategoryPerformance,
                    Demographics, GeographicalInsights, CustomerBehavior, Prediction
                ]
                for collection in collections_to_clear:
                    collection.objects().delete()
                logger.info("Successfully cleared existing analytics data")
            except Exception as clear_err:
                logger.error(f"Error clearing existing analytics data: {str(clear_err)}")
                raise

            # Update each analytics collection with error handling for each method
            analytics_methods = [
                (self.update_sales_trends, 'sales trends'),
                (self.update_product_performance, 'product performance'),
                (self.update_category_performance, 'category performance'),
                (self.update_demographics, 'demographics'),
                (self.update_geographical_insights, 'geographical insights'),
                (self.update_customer_behavior, 'customer behavior')
            ]

            success_count = 0
            for method, name in analytics_methods:
                try:
                    method()
                    success_count += 1
                    logger.info(f"Successfully updated {name} analytics")
                except Exception as method_err:
                    logger.error(f"Error updating {name} analytics: {str(method_err)}")
                    continue

            # Generate predictions after all analytics are updated
            try:
                self.predict_and_store_insights()
                success_count += 1
                logger.info("Successfully generated predictions")
            except Exception as pred_err:
                logger.error(f"Error generating predictions: {str(pred_err)}")

            if success_count == len(analytics_methods) + 1:  # +1 for predictions
                logger.info("Successfully completed all analytics and predictions updates")
            else:
                logger.warning(f"Completed {success_count} out of {len(analytics_methods) + 1} total updates")

        except Exception as e:
            logger.error(f"Critical error in update_analytics: {str(e)}")
            raise

    def update_sales_trends(self):
        """Update sales trends analytics"""
        try:
            pipeline = [
                {'$group': {
                    '_id': {  
                        'year': {'$year': '$sale_date'},
                        'month': {'$month': '$sale_date'}
                    },
                    'total_sales': {'$sum': '$revenue'},
                    'order_count': {'$sum': 1}
                }},
                {'$sort': {'_id.year': 1, '_id.month': 1}}
            ]
            
            monthly_sales = list(Sales.objects.aggregate(*pipeline))
            prev_sales = None

            for item in monthly_sales:
                period_value = f"{item['_id']['year']}-{item['_id']['month']:02d}"
                curr_sales = float(item['total_sales'])
                growth_rate = 0 if prev_sales is None else ((curr_sales - prev_sales) / prev_sales * 100)
                prev_sales = curr_sales

                total_sales_for_period = sum(s['total_sales'] for s in monthly_sales)
                sales_percentage = (curr_sales / total_sales_for_period * 100) if total_sales_for_period > 0 else 0

                trend_data = {
                    'period_type': 'monthly',
                    'period_value': period_value,
                    'total_sales': curr_sales,
                    'sales_growth_rate': float(growth_rate),
                    'sales_percentage': float(sales_percentage)
                }
                
                # Use update_one with upsert to avoid duplicates
                SalesTrend.objects(period_type='monthly', period_value=period_value).update_one(
                    upsert=True, 
                    **trend_data
                )

            logger.info("Successfully updated sales trends")
            return True

        except Exception as e:
            logger.error(f"Error updating sales trends: {str(e)}")
            raise

    def update_product_performance(self):
        """Update product performance analytics"""
        try:
            pipeline = [
                {'$group': {
                    '_id': '$product_id',
                    'total_quantity': {'$sum': '$quantity'},
                    'total_revenue': {'$sum': '$revenue'},
                    'total_profit': {'$sum': '$profit'}
                }},
                {'$sort': {'total_revenue': -1}}
            ]
            
            product_metrics = list(Sales.objects.aggregate(*pipeline))

            # Find best and worst selling products
            sorted_by_revenue = sorted(product_metrics, key=lambda x: x['total_revenue'], reverse=True)
            best_selling = sorted_by_revenue[0] if sorted_by_revenue else None
            worst_selling = sorted_by_revenue[-1] if sorted_by_revenue else None

            for item in product_metrics:
                product = Product.objects(product_id=item['_id']).first()
                if product:
                    performance_data = {
                        'product_id': str(product.id),
                        'category': product.category_name,
                        'total_quantity_sold': int(item['total_quantity']),
                        'average_revenue': float(item['total_revenue'] / item['total_quantity']) if item['total_quantity'] > 0 else 0,
                        'is_best_selling': item == best_selling,
                        'is_worst_selling': item == worst_selling,
                    }
                    
                    ProductPerformance.objects(product_id=str(product.id)).update_one(
                        upsert=True,
                        **performance_data
                    )

            logger.info("Successfully updated product performance")
            return True

        except Exception as e:
            logger.error(f"Error updating product performance: {str(e)}")
            raise

    def update_category_performance(self):
        """Update category performance analytics"""
        try:
            # Get all sales data with product information
            sales_data = Sales.objects().all()
            df = pd.DataFrame([{
                'category': Product.objects(product_id=sale.product_id).first().category_name,
                'quantity': sale.quantity,
                'revenue': float(sale.revenue),
                'profit': float(sale.profit)
            } for sale in sales_data])

            # Group by category and calculate metrics
            category_metrics = df.groupby('category').agg({
                'quantity': 'sum',
                'revenue': 'sum',
                'profit': 'sum'
            }).reset_index()

            # Find highest profit category
            highest_profit_category = category_metrics.loc[category_metrics['profit'].idxmax(), 'category']

            # Store in CategoryPerformance collection
            for _, row in category_metrics.iterrows():
                performance_data = {
                    'id': f"CAT-{row['category'].replace(' ', '-').lower()}",
                    'category': row['category'],
                    'total_quantity_sold': int(row['quantity']),
                    'average_revenue': float(row['revenue'] / row['quantity']) if row['quantity'] > 0 else 0,
                    'highest_profit': row['category'] == highest_profit_category
                }
                CategoryPerformance.objects(category=row['category']).update_one(upsert=True, **performance_data)

            logger.info("Successfully updated category performance analytics")
            return True

        except Exception as e:
            logger.error(f"Error updating category performance: {str(e)}")
            raise

    def update_demographics(self):
        """Update demographics analytics"""
        try:
            # Get customer data with their orders
            customers = Customer.objects().all()
            df = pd.DataFrame([{
                'gender': customer.gender,
                'age': customer.age,
                'city': customer.city,
                'total_orders': len(Order.objects(customer_id=customer)),
                'total_spent': sum(float(order.product_id.price * order.quantity) 
                                 for order in Order.objects(customer_id=customer))
            } for customer in customers])

            # Calculate age groups
            df['age_group'] = pd.cut(df['age'], 
                                   bins=[0, 25, 35, 50, 65, 100],
                                   labels=['18-25', '26-35', '36-50', '51-65', '65+'])

            # Group by different demographic factors
            gender_metrics = df.groupby('gender').agg({
                'total_orders': 'sum',
                'total_spent': 'mean'
            }).reset_index()

            age_metrics = df.groupby('age_group').agg({
                'total_orders': 'sum',
                'total_spent': 'mean'
            }).reset_index()

            # Store in Demographics collection
            for metric_type, metrics_df in [('gender', gender_metrics), ('age_group', age_metrics)]:
                for _, row in metrics_df.iterrows():
                    demographic_data = {
                        'segment_type': metric_type,
                        'segment_value': row[metric_type],
                        'total_orders': int(row['total_orders']),
                        'average_order_value': float(row['total_spent'])
                    }
                    Demographics.objects(
                        segment_type=metric_type,
                        segment_value=row[metric_type]
                    ).update_one(upsert=True, **demographic_data)

        except Exception as e:
            logger.error(f"Error updating demographics: {str(e)}")

    def update_geographical_insights(self):
        """Update geographical insights analytics"""
        try:
            # Get sales data with city information
            sales_data = Sales.objects().all()
            df = pd.DataFrame([{
                'city': sale.city,
                'revenue': float(sale.revenue),
                'quantity': sale.quantity
            } for sale in sales_data])

            # Group by city and calculate metrics
            city_metrics = df.groupby('city').agg({
                'revenue': 'sum',
                'quantity': 'sum'
            }).reset_index()

            # Calculate market share for each city
            total_revenue = city_metrics['revenue'].sum()
            city_metrics['market_share'] = city_metrics['revenue'] / total_revenue

            # Store in GeographicalInsights collection
            for _, row in city_metrics.iterrows():
                insight_data = {
                    'city': row['city'],
                    'total_revenue': float(row['revenue']),
                    'total_orders': int(row['quantity']),
                    'market_share': float(row['market_share'])
                }
                GeographicalInsights.objects(city=row['city']).update_one(upsert=True, **insight_data)

        except Exception as e:
            logger.error(f"Error updating geographical insights: {str(e)}")

    def update_customer_behavior(self):
        """Update customer behavior analytics"""
        try:
            # Get all orders with customer information and reviews
            orders_df = pd.DataFrame([{
                'customer_id': str(order.customer_id.id),
                'order_date': order.order_date,
                'quantity': order.quantity,
                'review_score': order.review_score if order.review_score else 0,
                'total_amount': float(order.product_id.price * order.quantity)
            } for order in Order.objects().all()])
            
            # Calculate sentiment before aggregating
            def get_sentiment(score):
                if score >= 4:
                    return 'Positive'
                elif score <= 2:
                    return 'Negative'
                return 'Neutral'
            
            # Group by customer and calculate metrics including review scores
            customer_metrics = orders_df.groupby('customer_id').agg({
                'order_date': ['count', 'min', 'max'],
                'quantity': 'sum',
                'total_amount': 'sum',
                'review_score': 'mean'
            }).reset_index()

            # Flatten column names
            customer_metrics.columns = ['customer_id', 'total_orders', 'first_purchase', 
                                     'last_purchase', 'total_items', 'total_spent', 'avg_review_score']

            # Store in CustomerBehavior collection
            for _, row in customer_metrics.iterrows():
                customer = Customer.objects(id=row['customer_id']).first()
                if customer:
                    behavior_data = {
                        'customer': customer,
                        'total_orders': int(row['total_orders']),
                        'total_spent': float(row['total_spent']),
                        'average_order_value': float(row['total_spent'] / row['total_orders']),
                        'first_purchase_date': row['first_purchase'],
                        'last_purchase_date': row['last_purchase'],
                        'average_review_score': float(row['avg_review_score']),
                    }
                    CustomerBehavior.objects(customer=customer).update_one(upsert=True, **behavior_data)

            logger.info("Successfully updated customer behavior analytics")
            return True

        except Exception as e:
            logger.error(f"Error updating customer behavior: {str(e)}")
            raise

    def get_sentiment(self, score):
        """Helper method to determine sentiment from review score"""
        if score >= 4:
            return 'Positive'
        elif score <= 2:
            return 'Negative'
        return 'Neutral'

    def predict_and_store_insights(self):
        """Generate and store predictions based on analyzed data"""
        try:
            # Get sales trends for future predictions
            sales_trends = SalesTrend.objects().all()
            if not sales_trends:
                logger.warning("No sales trends available for prediction")
                return

            # Future sales trend prediction
            recent_trends = list(sales_trends.order_by('-period_value')[:3])  # Last 3 periods
            if recent_trends:
                avg_growth = sum(trend.sales_growth_rate for trend in recent_trends) / len(recent_trends)
                latest_sales = recent_trends[0].total_sales
                predicted_sales = latest_sales * (1 + (avg_growth / 100))
                
                prediction_data = {
                    'id': f"PRED-SALES-{recent_trends[0].period_value}",
                    'prediction_type': 'future_sales_trend',
                    'prediction_period': 'next_month',
                    'predicted_value': f"{predicted_sales:.2f}",
                    'details': f"Based on average growth rate of {avg_growth:.1f}%"
                }
                Prediction.objects(prediction_type='future_sales_trend',
                                prediction_period='next_month').update_one(upsert=True, **prediction_data)

            # Future top product prediction
            top_products = ProductPerformance.objects(is_best_selling=True).first()
            if top_products:
                prediction_data = {
                    'id': f"PRED-PROD-{top_products.product_id}",
                    'prediction_type': 'future_top_product',
                    'prediction_period': 'next_quarter',
                    'predicted_value': top_products.product_id,
                    'details': f"Based on current performance metrics"
                }
                Prediction.objects(prediction_type='future_top_product',
                                prediction_period='next_quarter').update_one(upsert=True, **prediction_data)

            # Category correlation prediction
            top_category = CategoryPerformance.objects(highest_profit=True).first()
            if top_category:
                prediction_data = {
                    'id': f"PRED-CAT-{top_category.category.replace(' ', '-').lower()}",
                    'prediction_type': 'correlation',
                    'prediction_period': 'current',
                    'predicted_value': top_category.category,
                    'details': f"Strong correlation with profitability"
                }
                Prediction.objects(prediction_type='correlation',
                                prediction_period='current').update_one(upsert=True, **prediction_data)

            logger.info("Successfully generated and stored predictions")
            return True

        except Exception as e:
            logger.error(f"Error generating predictions: {str(e)}")
            raise