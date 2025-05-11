import logging
import pandas as pd
from decimal import Decimal
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from core.models import Customer, Product, Order, Sales, RawDataUpload, LowReview, HighReview
from core.utils import save_review_with_sharding, replicate_data, initialize_databases
from analytics.models import (
    SalesTrend, ProductPerformance, CategoryPerformance,
    Demographics, GeographicalInsights, CustomerBehavior, Prediction
)
from django.core.files.uploadedfile import UploadedFile
import json
from mongoengine.connection import get_db

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

            # Create upload record and replicate to both databases
            upload_data = {
                'file_name': file.name,
                'status': 'processing'
            }
            low_doc, high_doc = RawDataUpload.save_to_all(upload_data)
            upload = low_doc  # Use the low_review_score_db instance for further operations

            try:
                # Read CSV file
                df = pd.read_csv(file)
                
                # Set total records count and update both databases
                upload_data = {'total_records': len(df)}
                RawDataUpload.objects(id=upload.id).update_one(**upload_data)  # Update low_review_score_db
                RawDataUpload.objects(id=high_doc.id).update_one(**upload_data)  # Update high_review_score_db

                from core.utils import save_review_with_sharding, replicate_data, initialize_databases
                
                # Initialize databases to ensure all collections exist
                initialize_databases()
                
                # Process data and store in respective collections
                for index, row in df.iterrows():
                    try:                        # Create or update customer - replicate to both databases
                        customer_data = {
                            'customer_id': int(row['customer_id']),
                            'gender': str(row['gender']),
                            'age': int(row['age']),
                            'city': str(row['city'])
                        }
                        # Use replicate_data instead of update_one to ensure data exists in both databases
                        replicate_data(customer_data, Customer)                        # Create or update product - replicate to both databases
                        product_data = {
                            'product_id': int(row['product_id']),
                            'product_name': str(row['product_name']),
                            'category_id': int(row['category_id']),
                            'category_name': str(row['category_name']),
                            'price': float(row['price'])
                        }
                        # Use replicate_data instead of update_one to ensure data exists in both databases
                        replicate_data(product_data, Product)

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
                            else:                                # Create new order and replicate to both databases
                                replicate_data(order_data, Order)
                                logger.info(f"Created new order: {generated_order_id}")

                            # Create sales record with matching ID and replicate to both databases
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
                            replicate_data(sales_data, Sales)# Create review record if review score exists
                            if pd.notna(row.get('review_score')):
                                review_data = {
                                    'id': f"REV-{generated_order_id}",
                                    'customer_id': str(row['customer_id']),
                                    'product_id': str(row['product_id']),
                                    'review_score': float(row['review_score']),
                                    'sentiment': self.get_sentiment(float(row['review_score'])),
                                    'review_text': row.get('review_text', ''),
                                    'review_date': order_date
                                }
                                # Save review to appropriate database based on score
                                save_review_with_sharding(review_data)

                                # Update review counters
                                if review_data['review_score'] < 4:
                                    upload_data['low_reviews_count'] = (upload_data.get('low_reviews_count', 0) + 1)
                                else:
                                    upload_data['high_reviews_count'] = (upload_data.get('high_reviews_count', 0) + 1)

                            # Update analytics collections - one by one to isolate any issues
                            try:
                                self.update_product_performance(row, order_date)
                            except Exception as e:
                                logger.error(f"Error in update_product_performance: {str(e)}")
                            try:
                                self.update_category_performance(row)
                            except Exception as e:
                                logger.error(f"Error in update_category_performance: {str(e)}")
                                
                            try:
                                # Use the enhanced version that ensures proper replication for all period types
                                from core.enhanced_sales_trend import update_sales_trend_enhanced
                                update_sales_trend_enhanced(row, order_date)
                            except Exception as e:
                                logger.error(f"Error in update_sales_trend: {str(e)}")
                                
                            try:
                                self.update_demographics(row)
                            except Exception as e:
                                logger.error(f"Error in update_demographics: {str(e)}")
                                
                            try:
                                self.update_geographical_insights(row)
                            except Exception as e:
                                logger.error(f"Error in update_geographical_insights: {str(e)}")
                                
                            # Don't call predict_and_store_insights for every row - will be called once at the end
                            # self.predict_and_store_insights()

                            upload_data = {'processed_records': upload.processed_records + 1}
                            RawDataUpload.objects(id=upload.id).update_one(**upload_data)  # Update low_review_score_db
                            RawDataUpload.objects(id=high_doc.id).update_one(**upload_data)  # Update high_review_score_db
                            
                        except Exception as e:
                            logger.error(f"Error creating order for row {index}: {str(e)}")
                            continue

                    except Exception as row_error:
                        logger.error(f"Error processing row {index}: {str(row_error)}")
                        continue                # Update upload status in both databases
                upload_data = {'status': 'completed'}
                RawDataUpload.objects(id=upload.id).update_one(**upload_data)  # Update low_review_score_db
                RawDataUpload.objects(id=high_doc.id).update_one(**upload_data)  # Update high_review_score_db

                # Trigger analytics calculations
                self.update_analytics()
                
                # Run finalization to ensure proper replication of all data types
                try:
                    logger.info("Running finalization process to ensure data consistency...")
                    self.finalize_upload_processing()
                except Exception as finalize_error:
                    logger.error(f"Error in finalization process: {str(finalize_error)}")
                    # Don't fail the upload if finalization has issues

                return Response({
                    'message': 'Data uploaded and processed successfully',
                    'successful_records': upload.processed_records
                })

            except Exception as process_error:
                # Update error status in both databases
                upload_data = {
                    'status': 'failed',
                    'error_message': str(process_error)
                }
                RawDataUpload.objects(id=upload.id).update_one(**upload_data)  # Update low_review_score_db
                RawDataUpload.objects(id=high_doc.id).update_one(**upload_data)  # Update high_review_score_db
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
                    collection.objects.delete()
                logger.info("Successfully cleared existing analytics data")
            except Exception as clear_err:
                logger.error(f"Error clearing existing analytics data: {str(clear_err)}")
                raise

            # Aggregate sales data first
            sales_data = list(Sales.objects.all())
            success_count = 0

            # Process each sale record for analytics
            for sale in sales_data:
                try:
                    # Get related records
                    customer = Customer.objects(customer_id=sale.customer_id).first()
                    product = Product.objects(product_id=sale.product_id).first()
                    
                    if not customer or not product:
                        continue
                    
                    # Create row data for analytics
                    row = {
                        'product_id': sale.product_id,
                        'customer_id': sale.customer_id,
                        'quantity': sale.quantity,
                        'price': product.price,
                        'city': sale.city,
                        'category_name': product.category_name,
                        'gender': customer.gender,
                        'age': customer.age
                    }
                    
                    # Update individual analytics
                    self.update_product_performance(row, sale.sale_date)
                    self.update_category_performance(row)
                    self.update_demographics(row)
                    self.update_geographical_insights(row)
                except Exception as e:
                    logger.error(f"Error processing sale {sale.id} for analytics: {str(e)}")

            # Update aggregate analytics
            try:
                self.update_sales_trends()
                success_count += 1
            except Exception as e:
                logger.error(f"Error updating sales trends: {str(e)}")

            try:
                self.update_customer_behavior()
                success_count += 1
            except Exception as e:
                logger.error(f"Error updating customer behavior: {str(e)}")

            # Generate predictions
            try:
                self.predict_and_store_insights()
                success_count += 1
                logger.info("Successfully generated predictions")
            except Exception as pred_err:
                logger.error(f"Error generating predictions: {str(pred_err)}")

            if success_count >= 3:  # We expect at least 3 successful operations
                logger.info("Successfully completed core analytics and predictions updates")
            else:
                logger.warning(f"Only completed {success_count} out of 3 core analytics updates")

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
                    'id': f"TREND-monthly-{period_value}",
                    'period_type': 'monthly',
                    'period_value': period_value,
                    'total_sales': curr_sales,
                    'sales_growth_rate': float(growth_rate),
                    'sales_percentage': float(sales_percentage)
                }
                  # Use specialized sales trend replication function instead of generic replicate_data
                from core.sales_trend_utils import replicate_sales_trend_data
                replicate_sales_trend_data(trend_data)

            logger.info("Successfully updated sales trends")
            return True

        except Exception as e:
            logger.error(f"Error updating sales trends: {str(e)}")
            raise

    def update_product_performance(self, row, order_date):
        """Update product performance analytics"""
        try:
            product_data = {
                'id': f"PROD-{row['product_id']}",
                'product_id': str(row['product_id']),
                'category': row['category_name'],
                'total_quantity_sold': int(row['quantity']),
                'average_revenue': float(row['quantity'] * row['price']),
                'is_best_selling': False,
                'is_worst_selling': False
            }
            replicate_data(product_data, ProductPerformance)
        except Exception as e:
            logger.error(f"Error updating product performance: {str(e)}")

    def update_category_performance(self, row):
        """Update category performance analytics"""
        try:
            category_data = {
                'id': f"CAT-{row['category_name'].replace(' ', '-').lower()}",
                'category': row['category_name'],
                'total_quantity_sold': int(row['quantity']),
                'average_revenue': float(row['quantity'] * row['price'])
            }
            replicate_data(category_data, CategoryPerformance)        
        except Exception as e:
            logger.error(f"Error updating category performance: {str(e)}")
            
    def update_sales_trend(self, row, order_date):
        """Update sales trend analytics"""
        try:
            # Import the specialized sales trend replication function
            from core.sales_trend_utils import replicate_sales_trend_data, ensure_database_consistency
            
            # Create period identifiers
            day = order_date.strftime('%Y-%m-%d')
            week = order_date.strftime('%Y-W%V')
            month = order_date.strftime('%Y-%m')
            year = order_date.strftime('%Y')
            quarter = f"{year}-Q{(order_date.month-1)//3 + 1}"

            periods = [
                ('daily', day),
                ('weekly', week),
                ('monthly', month),
                ('quarterly', quarter),
                ('yearly', year)
            ]

            for period_type, period_value in periods:
                trend_data = {
                    'id': f"TREND-{period_type}-{period_value}",
                    'period_type': period_type,
                    'period_value': period_value,
                    'total_sales': float(row['quantity'] * row['price']),
                    'sales_growth_rate': 0.0,  # Will be calculated in batch
                    'sales_percentage': 0.0  # Will be calculated in batch
                }
                # Use specialized replication function instead of the generic one
                low_doc, high_doc = replicate_sales_trend_data(trend_data)
                
                # Additional verification to ensure data was actually written to both DBs
                if not low_doc or not high_doc:
                    logger.warning(f"Initial replication failed for {period_type}. Retrying with direct method...")
                    # Force consistency between databases as a failsafe
                    ensure_database_consistency(period_type, period_value)
                
        except Exception as e:
            logger.error(f"Error updating sales trend: {str(e)}")
            
    def update_demographics(self, row):
        """Update demographics analytics"""
        try:
            demographics_data = {
                'id': f"DEM-{row['gender']}-{row['age']//10*10}",
                'age_group': f"{row['age']//10*10}-{row['age']//10*10+9}",
                'gender': row['gender'],
                'total_customers': 1,
                'total_spent': float(row['quantity'] * row['price'])
            }
            replicate_data(demographics_data, Demographics)
        except Exception as e:
            logger.error(f"Error updating demographics: {str(e)}")
    
    def finalize_upload_processing(self):
        """Run post-processing steps after the CSV upload is complete"""
        try:
            logger.info("Running post-processing for CSV upload...")
            
            # Import the post-upload hook
            from post_upload_hooks import ensure_sales_trend_consistency
            
            # Ensure all sales trend data is properly replicated
            ensure_sales_trend_consistency()
            
            logger.info("Post-processing for CSV upload completed successfully")
        except Exception as e:
            logger.error(f"Error in post-upload processing: {str(e)}")

    def update_geographical_insights(self, row):
        """Update geographical insights analytics"""
        try:
            geo_data = {
                'id': f"GEO-{row['city'].replace(' ', '-').lower()}",
                'city': row['city'],
                'total_sales': float(row['quantity'] * row['price']),
                'total_orders': 1,
                'average_order_value': float(row['quantity'] * row['price'])
            }
            replicate_data(geo_data, GeographicalInsights)
        except Exception as e:
            logger.error(f"Error updating geographical insights: {str(e)}")
            
    def update_customer_behavior(self):
        """Update customer behavior analytics"""
        try:
            # Group sales by customer_id
            pipeline = [
                {'$group': {
                    '_id': '$customer_id',
                    'total_purchases': {'$sum': 1},
                    'total_spent': {'$sum': '$revenue'},
                    'purchase_frequency': {'$avg': '$quantity'}
                }}
            ]
            
            customers_behavior = list(Sales.objects.aggregate(*pipeline))
            
            for customer in customers_behavior:
                behavior_data = {
                    'id': f"CUST-{customer['_id']}",
                    'customer_id': customer['_id'],
                    'total_purchases': customer['total_purchases'],
                    'total_spent': float(customer['total_spent']),
                    'purchase_frequency': float(customer['purchase_frequency']),
                    'customer_segment': self.get_customer_segment(customer['total_spent'], customer['total_purchases'])
                }
                  # Use replicate_data to update both databases
                replicate_data(behavior_data, CustomerBehavior)
                
            logger.info("Successfully updated customer behavior")
            return True
            
        except Exception as e:
            logger.error(f"Error updating customer behavior: {str(e)}")
            raise
            
    def get_customer_segment(self, total_spent, purchase_count):
        """Helper function to determine customer segment based on spending and frequency"""
        if total_spent > 1000 and purchase_count > 10:
            return 'VIP'
        elif total_spent > 500 or purchase_count > 5:
            return 'Regular'
        else:
            return 'Occasional'

    def predict_and_store_insights(self):
        """Generate and store predictions based on analyzed data"""
        try:
            # Sales trend prediction
            recent_trends = SalesTrend.objects(period_type='monthly').order_by('-period_value')[:12]
            if recent_trends:
                total_growth = 0
                count = 0
                prev_sales = None
                
                for trend in recent_trends:
                    if prev_sales is not None:
                        growth = ((trend.total_sales - prev_sales) / prev_sales * 100) if prev_sales > 0 else 0
                        total_growth += growth
                        count += 1
                    prev_sales = trend.total_sales
                
                avg_growth = total_growth / count if count > 0 else 0
                
                prediction_data = {
                    'id': f"PRED-TREND-{pd.Timestamp.now().strftime('%Y%m')}",
                    'prediction_type': 'future_sales_trend',
                    'prediction_period': 'next_quarter',
                    'predicted_value': f"{avg_growth:.1f}",
                    'details': f"Based on average growth rate of {avg_growth:.1f}%"
                }
                replicate_data(prediction_data, Prediction)

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
                replicate_data(prediction_data, Prediction)
                
            # Customer churn prediction based on purchase patterns
            inactive_customers = CustomerBehavior.objects(total_purchases__lt=2).limit(10)
            if inactive_customers:
                for customer in inactive_customers:
                    prediction_data = {
                        'id': f"PRED-CHURN-{customer.customer_id}",
                        'prediction_type': 'churn_risk',
                        'prediction_period': 'next_quarter',
                        'predicted_value': 'high',
                        'details': f"Customer {customer.customer_id} with low engagement"
                    }
                    replicate_data(prediction_data, Prediction)
        except Exception as e:
            logger.error(f"Error generating predictions: {str(e)}")

    def get_sentiment(self, review_score):
        """Helper function to map review score to sentiment"""
        if review_score >= 4:
            return 'positive'
        elif review_score >= 3:
            return 'neutral'
        else:
            return 'negative'