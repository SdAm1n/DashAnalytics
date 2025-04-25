from django.urls import path
from .views import (
    index, dashboard, sales_trend, product_performance, demographics,
    geographical_insights, customer_behavior, prediction, data_upload,
    signin, signup, logout_view, profile
)

urlpatterns = [
    # Authentication URLs
    path('signin/', signin, name='signin'),
    path('signup/', signup, name='signup'),
    path('logout/', logout_view, name='logout'),
    path('profile/', profile, name='profile'),

    # Dashboard and analytics URLs
    path('', index, name='index'),
    path('dashboard/', dashboard, name='dashboard'),
    path('sales-trend/', sales_trend, name='sales_trend'),
    path('product-performance/', product_performance, name='product_performance'),
    path('demographics/', demographics, name='demographics'),
    path('geographical-insights/', geographical_insights,
         name='geographical_insights'),
    path('customer-behavior/', customer_behavior, name='customer_behavior'),
    path('prediction/', prediction, name='prediction'),
    path('data-upload/', data_upload, name='data_upload'),
]
