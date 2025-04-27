from .auth_views import AuthViewSet
from .customer_views import CustomerViewSet
from .product_views import ProductViewSet
from .order_views import OrderViewSet
from .analytics_views import AnalyticsViewSet
from .data_upload_views import DataUploadView

__all__ = [
    'AuthViewSet',
    'CustomerViewSet',
    'ProductViewSet',
    'OrderViewSet',
    'AnalyticsViewSet',
    'DataUploadView'
]