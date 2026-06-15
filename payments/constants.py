"""
Payment-related constants and configuration.
"""

# Premium Subscription Pricing
PREMIUM_PRICE_INR = 499  # Amount in INR
# Payment Configuration
PAYMENT_CURRENCY = "INR"
PAYMENT_CAPTURE_MODE = 1  # Auto-capture

# Celery Task Configuration
CELERY_MAX_RETRIES = 3  # Maximum retries for async tasks
CELERY_RETRY_BACKOFF_BASE = 60  # Base backoff in seconds (1 minute)

# Polling Configuration
POLLING_MAX_RETRIES = 10  # Maximum number of polling attempts
POLLING_BACKOFF_BASE = 300  # Base backoff in seconds (5 minutes)
POLLING_BACKOFF_MAX = 3600  # Maximum backoff in seconds (1 hour)
POLLING_CUTOFF_MINUTES = 2  # Minimum age before polling (avoid race conditions)
POLLING_BATCH_SIZE = 50  # Maximum payments to process per polling cycle
PAYMENT_ABANDON_MINUTES = 1440  # Abandon payments older than 24 hours

# Polling Backoff Intervals (exponential backoff thresholds)
POLLING_INTERVAL_THRESHOLD_1 = 5  # First threshold in minutes
POLLING_INTERVAL_THRESHOLD_2 = 15  # Second threshold in minutes
POLLING_INTERVAL_THRESHOLD_3 = 60  # Third threshold in minutes
POLLING_MODULO_1 = 2  # Poll every 2nd cycle for payments 5-15 min old
POLLING_MODULO_2 = 4  # Poll every 4th cycle for payments 15-60 min old
POLLING_MODULO_3 = 8  # Poll every 8th cycle for payments >60 min old

# Webhook Configuration
WEBHOOK_TIMEOUT_SECONDS = 30
