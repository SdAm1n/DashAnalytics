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