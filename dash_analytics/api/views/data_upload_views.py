import logging
import pandas as pd
from decimal import Decimal
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from core.models import Customer, Product, Order, Sales, RawDataUpload
from analytics.models import (
    Review, SalesTrend, ProductPerformance, CategoryPerformance,
    Demographics, GeographicalInsights, CustomerBehavior
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
            # Update sales trends
            self.update_sales_trends()
            
            # Update product performance
            self.update_product_performance()
            
            # Update category performance
            self.update_category_performance()
            
            # Update demographics
            self.update_demographics()
            
            # Update geographical insights
            self.update_geographical_insights()
            
            # Update customer behavior
            self.update_customer_behavior()

        except Exception as e:
            logger.error(f"Error updating analytics: {str(e)}")

    def update_sales_trends(self):
        """Update sales trends analytics"""
        sales_data = Sales.objects().all()
        # Implementation for sales trends calculation
        pass

    def update_product_performance(self):
        """Update product performance analytics"""
        sales_data = Sales.objects().all()
        # Implementation for product performance calculation
        pass

    def update_category_performance(self):
        """Update category performance analytics"""
        sales_data = Sales.objects().all()
        # Implementation for category performance calculation
        pass

    def update_demographics(self):
        """Update demographics analytics"""
        customer_data = Customer.objects().all()
        # Implementation for demographics calculation
        pass

    def update_geographical_insights(self):
        """Update geographical insights analytics"""
        sales_data = Sales.objects().all()
        # Implementation for geographical insights calculation
        pass

    def update_customer_behavior(self):
        """Update customer behavior analytics"""
        orders_data = Order.objects().all()
        # Implementation for customer behavior calculation
        pass