from django.db.models import TextChoices


class PaymentStatus(TextChoices):
    """
    Payment status choices
    """

    CREATED = "created", "Created"
    PAID = "paid", "Paid"
    VERIFIED = "verified", "Verified"
    ACTIVATED = "activated", "Activated"
    FAILED = "failed", "Failed"
    REFUNDED = "refunded", "Refunded"
    CANCELLED = "cancelled", "Cancelled"


class SubscriptionStatus(TextChoices):
    """
    Subscription status choices
    """

    NONE = "none", "No Subscription"
    ACTIVE = "active", "Active"
    EXPIRED = "expired", "Expired"


class WebhookEventStatus(TextChoices):
    """
    Webhook event status choices
    """

    PENDING = "pending", "Pending"
    PROCESSING = "processing", "Processing"
    PROCESSED = "processed", "Processed"
    FAILED = "failed", "Failed"
