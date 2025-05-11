"""
Optimized Data Upload Views for DashAnalytics

Provides enhanced data processing functionality with support for:
- Bulk inserts
- Threading
- Background processing for large files
- Optimized database operations
"""

import logging
import pandas as pd
import os
import tempfile
from decimal import Decimal
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from core.models import Customer, Product, Order, Sales, RawDataUpload
from core.utils import initialize_databases
from core.fixed_bulk_processor import FixedBulkProcessor as BulkDataProcessor
from core.bulk_sales_trend import update_sales_trend_in_bulk
from analytics.models import (
    SalesTrend, ProductPerformance, CategoryPerformance,
    Demographics, GeographicalInsights, CustomerBehavior, Prediction
)
from django.core.files.uploadedfile import UploadedFile
import json
from mongoengine.connection import get_db

# Import Celery tasks if using background processing
try:
    from celery_app import process_csv_data_task, process_analytics_task
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    logging.warning("Celery not available, background processing will be disabled")

logger = logging.getLogger(__name__)

class DataUploadView(APIView):
    """
    Optimized API view for data uploads and processing
    """
    def post(self, request):
        """
        Handle CSV file upload with optimized processing
        """
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

            # Create upload record with pending status
            upload_data = {
                'file_name': file.name,
                'status': 'pending'
            }
            low_doc, high_doc = RawDataUpload.save_to_all(upload_data)
            upload_id = low_doc.id  # Use ID for passing to background tasks
            
            # Determine processing method based on file size
            file_size = file.size
            is_large_file = file_size > 5 * 1024 * 1024  # 5MB threshold
            
            # If Celery is available and file is large, process in background
            if CELERY_AVAILABLE and is_large_file:
                # Save uploaded file to a temporary location
                with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as temp_file:
                    for chunk in file.chunks():
                        temp_file.write(chunk)
                    temp_file_path = temp_file.name
                
                # Start background processing task
                process_csv_data_task.delay(upload_id, temp_file_path)
                
                # Return 202 Accepted for background processing
                return Response({
                    'message': 'File upload accepted for processing',
                    'upload_id': str(upload_id),
                    'status': 'pending',
                    'is_background_process': True
                }, status=status.HTTP_202_ACCEPTED)
            else:
                # For smaller files or when Celery isn't available, process synchronously
                try:
                    # Update status to processing
                    upload_data = {'status': 'processing'}
                    RawDataUpload.objects(id=upload_id).update_one(**upload_data)
                    RawDataUpload.objects(id=high_doc.id).update_one(**upload_data)
                    
                    # Read CSV file
                    df = pd.read_csv(file)
                    
                    # Initialize databases to ensure all collections exist
                    initialize_databases()
                      # Process data in bulk with optimized operations
                    processor = BulkDataProcessor(chunk_size=200)
                    result = processor.process_dataframe(df, upload_id)
                    
                    # Process sales trends in bulk
                    update_sales_trend_in_bulk(df)
                    
                    # Update upload record with counts and processing time
                    completed_data = {
                        'status': 'completed',
                        'processed_records': result['processed_records'],
                        'total_records': result['total_records'],
                        'high_reviews_count': result['high_reviews_count'],
                        'low_reviews_count': result['low_reviews_count'],
                        'processing_time': result['processing_time']
                    }
                    RawDataUpload.objects(id=upload_id).update_one(**completed_data)
                    RawDataUpload.objects(id=high_doc.id).update_one(**completed_data)
                    
                    # Run post-processing hooks if available
                    try:
                        from post_upload_hooks import post_csv_upload_hook
                        post_csv_upload_hook()
                    except Exception as hook_error:
                        logger.error(f"Error running post upload hooks: {str(hook_error)}")
                    
                    # Return success response
                    return Response({
                        'message': 'Data uploaded and processed successfully',
                        'upload_id': str(upload_id),
                        'processed_records': result['processed_records'],
                        'high_reviews': result['high_reviews_count'],
                        'low_reviews': result['low_reviews_count'],
                        'processing_time_seconds': result['processing_time']
                    })

                except Exception as process_error:
                    # Update status to failed
                    error_data = {
                        'status': 'failed',
                        'error_message': str(process_error)
                    }
                    RawDataUpload.objects(id=upload_id).update_one(**error_data)
                    RawDataUpload.objects(id=high_doc.id).update_one(**error_data)
                    
                    logger.error(f"Error processing data upload: {str(process_error)}")
                    return Response(
                        {'error': 'Error processing upload: ' + str(process_error)}, 
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
        
        except Exception as e:
            logger.error(f"Error handling upload request: {str(e)}")
            return Response(
                {'error': 'Error handling upload: ' + str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def get_upload_status(self, request, upload_id):
        """
        Get status of a background upload process
        """
        try:
            upload = RawDataUpload.objects(id=upload_id).first()
            if not upload:
                return Response({'error': 'Upload not found'}, status=status.HTTP_404_NOT_FOUND)
            
            return Response({
                'upload_id': str(upload.id),
                'status': upload.status,
                'file_name': upload.file_name,
                'processed_records': upload.processed_records,
                'total_records': upload.total_records,
                'high_reviews': getattr(upload, 'high_reviews_count', 0),
                'low_reviews': getattr(upload, 'low_reviews_count', 0),
                'error_message': getattr(upload, 'error_message', None),
                'processing_time_seconds': getattr(upload, 'processing_time', None)
            })
            
        except Exception as e:
            logger.error(f"Error getting upload status: {str(e)}")
            return Response(
                {'error': 'Error getting upload status: ' + str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def get_sentiment(self, score):
        """Convert review score to sentiment label"""
        if score >= 4:
            return 'Positive'
        elif score <= 2:
            return 'Negative'
        return 'Neutral'
