default_app_config = 'analytics.apps.AnalyticsConfig'

# Import the sales trend fix to automatically patch the model
try:
    # This import will automatically apply the patch when the app is loaded
    from .sales_trend_fix import patch_sales_trend_model
    # Import during Django startup to ensure patch is applied
except ImportError:
    import logging
    logging.getLogger(__name__).warning("Could not load sales_trend_fix module")