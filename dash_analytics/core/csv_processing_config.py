"""
Configuration settings for optimized CSV processing

This module provides configuration settings for the optimized CSV processing
functionality in the DashAnalytics application.
"""

# Bulk processing settings
BULK_PROCESSING = {
    'CHUNK_SIZE': 1000,          # Number of records to process in a single batch
    'MAX_THREADS': 4,            # Maximum number of worker threads for parallel processing
    'LARGE_FILE_THRESHOLD': 5,   # Size in MB to trigger background processing
    'MEMORY_LIMIT': 512,         # Maximum memory usage in MB before switching to disk-based processing
}

# MongoDB optimization settings
MONGODB_OPTIMIZATIONS = {
    'WRITE_CONCERN': 1,          # Write concern for bulk operations (0-2)
    'READ_PREFERENCE': 'primary',# Read preference for database operations
    'ORDERED_WRITES': False,     # Whether bulk writes should be ordered (slower but safer)
    'CONNECTION_POOL_SIZE': 100, # Size of connection pool for MongoDB
}

# Celery task settings for background processing
CELERY_TASK_SETTINGS = {
    'DEFAULT_RETRY_DELAY': 30,   # Default retry delay in seconds
    'MAX_RETRIES': 3,            # Maximum number of retries for failed tasks
    'IGNORE_RESULT': True,       # Whether to ignore task results (faster)
    'RESULT_EXPIRES': 3600,      # Time in seconds before task results expire
}

# Thread pool settings
THREAD_POOL_SETTINGS = {
    'QUEUE_SIZE': 1000,          # Size of task queue for thread pool
    'THREAD_TIMEOUT': 60,        # Timeout in seconds for worker threads
    'ERROR_HANDLING': 'continue',# Error handling strategy ('continue' or 'abort')
}

# Performance monitoring settings
PERFORMANCE_MONITORING = {
    'ENABLED': True,             # Whether to enable performance monitoring
    'LOG_LEVEL': 'INFO',         # Log level for performance monitoring
    'METRICS': [                 # Metrics to collect
        'processing_time',
        'memory_usage',
        'database_operations',
        'errors',
    ],
    'ALERT_THRESHOLD': 30,       # Threshold in seconds for slow operations alerts
}
