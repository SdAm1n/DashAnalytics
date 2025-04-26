from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from core.models import Customer, Order
from api.serializers import CustomerSerializer
from django.http import Http404

class CustomerViewSet(viewsets.ViewSet):
    """
    API endpoint for customers
    """

    def list(self, request):
        customers = Customer.objects.all()
        serializer = CustomerSerializer(customers, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        try:
            customer = Customer.objects.get(id=pk)
        except Customer.DoesNotExist:
            raise Http404

        serializer = CustomerSerializer(customer)
        return Response(serializer.data)

    def create(self, request):
        serializer = CustomerSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None):
        try:
            customer = Customer.objects.get(id=pk)
        except Customer.DoesNotExist:
            raise Http404

        serializer = CustomerSerializer(customer, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        try:
            customer = Customer.objects.get(id=pk)
        except Customer.DoesNotExist:
            raise Http404

        serializer = CustomerSerializer(customer, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        try:
            customer = Customer.objects.get(id=pk)
        except Customer.DoesNotExist:
            raise Http404

        customer.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'])
    def demographics(self, request):
        """
        Get customer demographics data for visualization
        """
        try:
            # Get age distribution
            age_distribution = Customer.objects.aggregate([
                {"$group": {
                    "_id": {
                        "$switch": {
                            "branches": [
                                {"case": {"$lt": ["$age", 18]}, "then": "Under 18"},
                                {"case": {"$and": [{"$gte": ["$age", 18]}, {"$lt": ["$age", 25]}]}, "then": "18-24"},
                                {"case": {"$and": [{"$gte": ["$age", 25]}, {"$lt": ["$age", 35]}]}, "then": "25-34"},
                                {"case": {"$and": [{"$gte": ["$age", 35]}, {"$lt": ["$age", 45]}]}, "then": "35-44"},
                                {"case": {"$and": [{"$gte": ["$age", 45]}, {"$lt": ["$age", 55]}]}, "then": "45-54"},
                                {"case": {"$and": [{"$gte": ["$age", 55]}, {"$lt": ["$age", 65]}]}, "then": "55-64"}
                            ],
                            "default": "65+"
                        }
                    },
                    "count": {"$sum": 1}
                }},
                {"$sort": {"_id": 1}}
            ])

            # Get gender distribution
            gender_distribution = Customer.objects.aggregate([
                {"$group": {
                    "_id": "$gender",
                    "count": {"$sum": 1}
                }}
            ])

            # Get location distribution
            location_distribution = Customer.objects.aggregate([
                {"$group": {
                    "_id": "$location",
                    "count": {"$sum": 1}
                }},
                {"$sort": {"count": -1}},
                {"$limit": 10}
            ])

            return Response({
                'age_groups': {group['_id']: group['count'] for group in age_distribution},
                'gender': {group['_id']: group['count'] for group in gender_distribution},
                'locations': {group['_id']: group['count'] for group in location_distribution}
            })
        except Exception as e:
            print(f"Error in demographics view: {str(e)}")
            return Response({"error": "Failed to fetch demographics data"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)