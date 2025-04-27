from django.urls import path, include
from .views.data_upload_views import DataUploadView
from .views.customer_views import CustomerViewSet
from .views.product_views import ProductViewSet
from .views.order_views import OrderViewSet

urlpatterns = [
    path('upload/', DataUploadView.as_view(), name='data-upload'),
    path('customers/', CustomerViewSet.as_view({'get': 'list'}), name='customer-list'),
    path('products/', ProductViewSet.as_view({'get': 'list'}), name='product-list'),
    path('orders/', OrderViewSet.as_view({'get': 'list'}), name='order-list'),
]
