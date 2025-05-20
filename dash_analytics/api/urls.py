from django.urls import path, include
from .views.data_upload_views import DataUploadView
from .views.customer_views import CustomerViewSet
from .views.product_views import ProductViewSet
from .views.order_views import OrderViewSet
from .views.analytics_views import AnalyticsViewSet
from analytics.api_views import SalesTrendView, CustomerBehaviorView, DemographicsView
from analytics.prediction_views import PredictionView
from analytics.geographical_views import GeographicalView
from analytics.product_performance_views import product_performance_api

urlpatterns = [
    path('upload/', DataUploadView.as_view(), name='data-upload'),
    path('upload/status/<str:upload_id>/',
         DataUploadView.as_view(), name='upload-status'),
    path('customers/',
         CustomerViewSet.as_view({'get': 'list'}), name='customer-list'),
    path('customers/demographics/',
         DemographicsView.as_view(), name='customer-demographics-api'),
    path('products/',
         ProductViewSet.as_view({'get': 'list'}), name='product-list'),
    path('products/top_sellers/',
         ProductViewSet.as_view({'get': 'top_sellers'}), name='top-sellers'),
    path('orders/', OrderViewSet.as_view({'get': 'list'}), name='order-list'),
    path('orders/sales_trend/',
         SalesTrendView.as_view(), name='sales-trend-api'),
    path('analytics/dashboard_summary/',
         AnalyticsViewSet.as_view({'get': 'dashboard_summary'}), name='dashboard-summary'),
    path('analytics/sales_trend/', SalesTrendView.as_view(), name='sales-trend-api'),
    path('analytics/customer_behavior/',
         CustomerBehaviorView.as_view(), name='customer-behavior-api'),
    path('analytics/demographics/',
         DemographicsView.as_view(), name='demographics-api'),
    path('analytics/predictions/', PredictionView.as_view(), name='predictions-api'),
    path('analytics/geographical/',
         GeographicalView.as_view(), name='geographical-api'),
    path('analytics/product_performance/',
         product_performance_api, name='product-performance-api'),
]
