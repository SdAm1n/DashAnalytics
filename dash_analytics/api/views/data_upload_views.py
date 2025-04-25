import logging
import datetime
import pandas as pd
from decimal import Decimal
import uuid
import hashlib

try:
    from django.http import Http404
    from django.conf import settings
    from rest_framework import viewsets, status
    from rest_framework.response import Response
    from rest_framework.decorators import action
except ImportError as e:
    logging.error(f"Django import error: {str(e)}")
    raise

try:
    from mongoengine.errors import ValidationError, NotUniqueError
    from pymongo.errors import ConnectionFailure
    from mongoengine import connect, disconnect
except ImportError as e:
    logging.error(f"Mongoengine import error: {str(e)}")
    raise

try:
    from core.models import RawDataUpload, Customer, Product, Order, OrderItem
except ImportError as e:
    logging.error(f"Local models import error: {str(e)}")
    raise

logger = logging.getLogger(__name__)

class DataUploadViewSet(viewsets.ViewSet):
    """
    API endpoint for data uploads and processing
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ensure MongoDB connection is established
        try:
            disconnect()  # Disconnect any existing connections
            connect(
                db=settings.MONGODB_NAME,
                host=settings.MONGODB_URI,
                connect=False
            )
        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {str(e)}")
            raise

    def _calculate_file_hash(self, file):
        """
        Calculate SHA-256 hash of file contents
        """
        sha256_hash = hashlib.sha256()
        for chunk in file.chunks():
            sha256_hash.update(chunk)
        return sha256_hash.hexdigest()

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
        try:
            if 'file' not in request.FILES:
                return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

            csv_file = request.FILES['file']

            if not csv_file.name.endswith('.csv'):
                return Response({'error': 'File must be a CSV'}, status=status.HTTP_400_BAD_REQUEST)

            # Calculate file hash and check for duplicates
            file_hash = self._calculate_file_hash(csv_file)
            csv_file.seek(0)  # Reset file pointer to beginning after calculating hash
            
            existing_upload = RawDataUpload.objects(file_hash=file_hash).first()
            if existing_upload:
                return Response({
                    'error': 'This file has already been uploaded',
                    'upload_date': existing_upload.upload_date,
                    'file_name': existing_upload.file_name
                }, status=status.HTTP_400_BAD_REQUEST)

            # Create a new RawDataUpload instance
            upload = RawDataUpload(
                file_name=csv_file.name,
                upload_date=datetime.datetime.now(),
                file_size=csv_file.size,
                file_hash=file_hash,
                processed=False
            )

            try:
                # Read CSV data
                df = pd.read_csv(csv_file)
            except pd.errors.EmptyDataError:
                return Response({'error': 'The CSV file is empty'}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                return Response({'error': f'Error reading CSV file: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
                
            # Validate required columns
            required_columns = ['customer_id', 'order_date', 'product_id', 'product_name', 
                              'category_name', 'quantity', 'price', 'payment_method', 'city']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                return Response({
                    'error': f'Missing required columns: {", ".join(missing_columns)}'
                }, status=status.HTTP_400_BAD_REQUEST)

            upload.row_count = len(df)
            upload.save()

            successful_records = 0
            errors = []

            # Get MongoDB connection
            db = connect(
                db=settings.MONGODB_NAME,
                host=settings.MONGODB_URI,
                connect=False
            )
            
            # Start a transaction session
            with db.start_session() as session:
                session.start_transaction()
                
                try:
                    # Process and store data in MongoDB
                    for index, row in df.iterrows():
                        try:
                            # Create or update Customer with all fields
                            customer_data = {
                                'customer_id': str(row['customer_id']),
                                'name': f'Customer_{row["customer_id"]}',  # Generate default name
                                'email': f'customer_{row["customer_id"]}@example.com',  # Generate default email
                                'gender': str(row['gender']).title() if pd.notna(row['gender']) else None,
                                'age': int(row['age']) if pd.notna(row['age']) else None,
                                'location': row['city'],
                                'registration_date': datetime.datetime.now()  # Set current time as registration
                            }
                            
                            try:
                                customer = Customer.objects(customer_id=customer_data['customer_id']).modify(
                                    upsert=True,
                                    new=True,
                                    set__name=customer_data['name'],
                                    set__email=customer_data['email'],
                                    set__gender=customer_data['gender'],
                                    set__age=customer_data['age'],
                                    set__location=customer_data['location'],
                                    set_on_insert__registration_date=customer_data['registration_date']
                                )
                            except ValidationError as e:
                                logger.error(f"Customer validation error: {str(e)}")
                                raise

                            # Create or update Product
                            product_data = {
                                'product_id': str(row['product_id']),
                                'name': row['product_name'],
                                'category': row['category_name'],
                                'price': Decimal(str(row['price'])),
                            }
                            
                            # Include rating if available
                            if 'review_score' in row and pd.notna(row['review_score']):
                                product_data['rating'] = float(row['review_score'])
                            
                            try:
                                product = Product.objects(product_id=product_data['product_id']).modify(
                                    upsert=True,
                                    new=True,
                                    set__name=product_data['name'],
                                    set__category=product_data['category'],
                                    set__price=product_data['price'],
                                    set__rating=product_data.get('rating')
                                )
                            except ValidationError as e:
                                logger.error(f"Product validation error: {str(e)}")
                                raise

                            # Create Order with OrderItem
                            try:
                                order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
                                order = Order(
                                    order_id=order_id,
                                    customer=customer,
                                    order_date=datetime.datetime.strptime(row['order_date'], '%Y-%m-%d'),
                                    payment_method=row['payment_method'],
                                    order_status='Delivered'  # Set a default status
                                )

                                order_item = OrderItem(
                                    product=product,
                                    quantity=int(row['quantity']),
                                    price=Decimal(str(row['price']))
                                )

                                order.items = [order_item]
                                
                                # Calculate total amount
                                order.total_amount = order_item.price * order_item.quantity
                                order.save()

                                # Update customer's last purchase date
                                customer.update(set__last_purchase_date=order.order_date)
                            except ValidationError as e:
                                logger.error(f"Order validation error: {str(e)}")
                                raise

                            successful_records += 1

                        except (ValidationError, NotUniqueError) as e:
                            errors.append(f"Error in row {index + 1}: {str(e)}")
                            continue
                        except Exception as e:
                            logger.error(f"Unexpected error processing row {index + 1}: {str(e)}")
                            errors.append(f"Unexpected error in row {index + 1}: {str(e)}")
                            continue

                    # Commit transaction if all went well
                    session.commit_transaction()
                    
                except Exception as e:
                    # Rollback transaction on error
                    session.abort_transaction()
                    logger.error(f"Transaction error: {str(e)}")
                    upload.delete()
                    return Response({
                        'error': f'Database transaction error: {str(e)}'
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # Mark upload as processed
            upload.processed = True
            upload.processed_date = datetime.datetime.now()
            upload.save()

            response_data = {
                'message': 'File uploaded and processed',
                'upload_id': str(upload.id),
                'total_rows': upload.row_count,
                'successful_records': successful_records,
                'failed_records': len(errors)
            }

            if errors:
                response_data['errors'] = errors[:10]  # Show first 10 errors only
                if len(errors) > 10:
                    response_data['note'] = f'Showing first 10 of {len(errors)} errors'

            return Response(response_data, 
                          status=status.HTTP_201_CREATED if successful_records > 0 
                          else status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Upload processing error: {str(e)}")
            if 'upload' in locals() and upload:
                upload.delete()  # Clean up the upload record if processing fails
            return Response({
                'error': f'Error processing file: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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

        # Update the upload record to mark as processed
        upload.processed = True
        upload.processed_date = datetime.datetime.now()
        upload.save()

        return Response({'message': 'File processing completed'}, status=status.HTTP_200_OK)