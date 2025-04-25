from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CustomerViewSet, 
    ProductViewSet, 
    OrderViewSet, 
    AnalyticsViewSet,
    DataUploadViewSet,
    register,
    login,
    logout
)

router = DefaultRouter()
router.register(r'customers', CustomerViewSet, basename='customer')
router.register(r'products', ProductViewSet, basename='product')
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'analytics', AnalyticsViewSet, basename='analytics')
router.register(r'data-uploads', DataUploadViewSet, basename='data-upload')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/register/', register, name='register'),
    path('auth/login/', login, name='login'),
    path('auth/logout/', logout, name='logout'),
]
