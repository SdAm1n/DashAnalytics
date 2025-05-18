"""
Prediction API views for showing future sales trend and future top product
from both high_review_score_db and low_review_score_db
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .models import Prediction
import json

class PredictionView(APIView):
    """API endpoint for prediction data (future sales trend and future top product)"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get prediction data from both databases"""
        try:
            # Get future sales trend predictions from low_review_score_db
            low_review_future_sales = Prediction.objects(
                prediction_type='future_sales_trend'
            ).using('low_review_score_db').order_by('-prediction_period').limit(3)

            # Get future sales trend predictions from high_review_score_db
            high_review_future_sales = Prediction.objects(
                prediction_type='future_sales_trend'
            ).using('high_review_score_db').order_by('-prediction_period').limit(3)

            # Get future top product predictions from low_review_score_db
            low_review_top_products = Prediction.objects(
                prediction_type='future_top_product'
            ).using('low_review_score_db').order_by('-prediction_period').limit(3)

            # Get future top product predictions from high_review_score_db
            high_review_top_products = Prediction.objects(
                prediction_type='future_top_product'
            ).using('high_review_score_db').order_by('-prediction_period').limit(3)

            # Format the data
            data = {
                'low_review_score_db': {
                    'future_sales_trend': [self._format_prediction(prediction) for prediction in low_review_future_sales],
                    'future_top_product': [self._format_prediction(prediction) for prediction in low_review_top_products]
                },
                'high_review_score_db': {
                    'future_sales_trend': [self._format_prediction(prediction) for prediction in high_review_future_sales],
                    'future_top_product': [self._format_prediction(prediction) for prediction in high_review_top_products]
                }
            }

            return Response(data)
        
        except Exception as e:
            return Response(
                {'error': f'Failed to retrieve prediction data: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _format_prediction(self, prediction):
        """Format a prediction object for API response"""
        details = {}
        if prediction.details:
            try:
                details = json.loads(prediction.details)
            except json.JSONDecodeError:
                details = {"raw_details": prediction.details}
        
        return {
            'id': str(prediction.id),
            'prediction_type': prediction.prediction_type,
            'prediction_period': prediction.prediction_period,
            'predicted_value': prediction.predicted_value,
            'details': details
        }
