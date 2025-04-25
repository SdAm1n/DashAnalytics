from .auth_views import register, login, logout
from .customer_views import CustomerViewSet
from .product_views import ProductViewSet
from .order_views import OrderViewSet
from .analytics_views import AnalyticsViewSet
from .data_upload_views import DataUploadViewSet

__all__ = [
    'register',
    'login',
    'logout',
    'CustomerViewSet',
    'ProductViewSet',
    'OrderViewSet',
    'AnalyticsViewSet',
    'DataUploadViewSet'
]