"""
Business logic for webhook event processing.

This module contains webhook-related business logic for handling Razorpay
webhook events, ensuring idempotency, and processing payment.captured events.
"""

import logging
from typing import Any, Dict

from django.db import transaction
from django.utils import timezone

from core.context import get_correlation_id
from payments.enums import PaymentStatus, WebhookEventStatus
from payments.models import Payment, WebhookEvent

logger = logging.getLogger(__name__)


class WebhookService:
    @staticmethod
    def is_duplicate_event(event_id: str) -> bool:
        """Check if webhook event already processed."""
        return WebhookEvent.objects.filter(event_id=event_id).exists()

    @staticmethod
    @transaction.atomic
    def log_webhook_event(
        event_id: str,
        event_type: str,
        payload: Dict[str, Any],
        raw_body: str,
        status: str = WebhookEventStatus.PENDING,
    ) -> WebhookEvent:
        """
        Log webhook event for idempotency and audit.
        """
        webhook_event = WebhookEvent.objects.create(
            event_id=event_id,
            event_type=event_type,
            payload=payload,
            raw_body=raw_body,
            status=status,
        )

        logger.info(
            f"Logged webhook event {event_id} - {event_type}",
            extra={"correlation_id": get_correlation_id(), "event_id": event_id},
        )
        return webhook_event

    @staticmethod
    def _resolve_payment(payload: Dict[str, Any], webhook_event: WebhookEvent):
        """
        Extract order/payment IDs from a webhook payload and load the locked Payment.

        On a missing field or unknown order, marks the webhook_event FAILED, saves it,
        and returns None. On success returns (payment, razorpay_payment_id).
        """
        payment_entity = (
            payload.get("payload", {}).get("payment", {}).get("entity", {})
        )

        razorpay_order_id = payment_entity.get("order_id")
        razorpay_payment_id = payment_entity.get("id")

        if not razorpay_order_id or not razorpay_payment_id:
            logger.error(
                "Missing order_id or payment_id in webhook payload",
                extra={"correlation_id": get_correlation_id()},
            )
            webhook_event.status = WebhookEventStatus.FAILED
            webhook_event.error_message = "Missing required fields in payload"
            webhook_event.save()
            return None

        try:
            payment = Payment.objects.select_for_update().get(
                razorpay_order_id=razorpay_order_id
            )
        except Payment.DoesNotExist:
            logger.error(
                f"Payment not found for order_id: {razorpay_order_id}",
                extra={
                    "correlation_id": get_correlation_id(),
                    "order_id": razorpay_order_id,
                },
            )
            webhook_event.status = WebhookEventStatus.FAILED
            webhook_event.error_message = f"Payment not found: {razorpay_order_id}"
            webhook_event.save()
            return None

        return (payment, razorpay_payment_id)

    @staticmethod
    @transaction.atomic
    def process_payment_captured(
        payload: Dict[str, Any], webhook_event: WebhookEvent
    ) -> bool:
        """
        Process payment.captured webhook event.
        """
        try:
            resolved = WebhookService._resolve_payment(payload, webhook_event)
            if resolved is None:
                return False
            payment, razorpay_payment_id = resolved

            if payment.status in [PaymentStatus.VERIFIED, PaymentStatus.ACTIVATED]:
                logger.info(
                    f"Payment {payment.id} already verified/activated, skipping webhook",
                    extra={
                        "correlation_id": get_correlation_id(),
                        "payment_id": str(payment.id),
                    },
                )
                webhook_event.status = WebhookEventStatus.PROCESSED
                webhook_event.processed_at = timezone.now()
                webhook_event.save()
                return True

            if payment.can_transition_to(PaymentStatus.PAID):
                payment.status = PaymentStatus.PAID
                payment.razorpay_payment_id = razorpay_payment_id
                payment.mark_verified()
                payment.save()

                from payments.services.payment_services import PaymentService

                PaymentService.activate_premium(str(payment.id))

                logger.info(
                    f"Payment {payment.id} marked as PAID, VERIFIED and ACTIVATED via webhook",
                    extra={
                        "correlation_id": get_correlation_id(),
                        "payment_id": str(payment.id),
                    },
                )

            webhook_event.status = WebhookEventStatus.PROCESSED
            webhook_event.processed_at = timezone.now()
            webhook_event.save()

            logger.info(
                f"Webhook event {webhook_event.event_id} processed successfully",
                extra={
                    "correlation_id": get_correlation_id(),
                    "event_id": webhook_event.event_id,
                },
            )
            return True

        except Exception as e:
            logger.error(
                f"Error processing webhook event {webhook_event.event_id}: {e}",
                extra={
                    "correlation_id": get_correlation_id(),
                    "event_id": webhook_event.event_id,
                },
            )
            webhook_event.status = WebhookEventStatus.FAILED
            webhook_event.error_message = str(e)
            webhook_event.retry_count += 1
            webhook_event.save()
            return False

    @staticmethod
    @transaction.atomic
    def process_payment_failed(
        payload: Dict[str, Any], webhook_event: WebhookEvent
    ) -> bool:
        """
        Process payment.failed webhook event.
        """
        try:
            resolved = WebhookService._resolve_payment(payload, webhook_event)
            if resolved is None:
                return False
            payment, razorpay_payment_id = resolved

            if payment.status in [
                PaymentStatus.VERIFIED,
                PaymentStatus.ACTIVATED,
                PaymentStatus.FAILED,
            ]:
                logger.info(
                    f"Payment {payment.id} already in terminal state ({payment.status}), skipping webhook",
                    extra={
                        "correlation_id": get_correlation_id(),
                        "payment_id": str(payment.id),
                        "status": payment.status,
                    },
                )
                webhook_event.status = (
                    WebhookEventStatus.FAILED
                    if payment.status == PaymentStatus.FAILED
                    else WebhookEventStatus.PROCESSED
                )
                webhook_event.processed_at = timezone.now()
                webhook_event.save()
                return True

            if payment.can_transition_to(PaymentStatus.FAILED):
                payment.status = PaymentStatus.FAILED
                payment.razorpay_payment_id = razorpay_payment_id
                payment.save()
                logger.info(
                    f"Payment {payment.id} marked as FAILED via webhook",
                    extra={
                        "correlation_id": get_correlation_id(),
                        "payment_id": str(payment.id),
                    },
                )

            webhook_event.status = WebhookEventStatus.FAILED
            webhook_event.processed_at = timezone.now()
            webhook_event.save()

            logger.info(
                f"Webhook event {webhook_event.event_id} processed successfully",
                extra={
                    "correlation_id": get_correlation_id(),
                    "event_id": webhook_event.event_id,
                },
            )
            return True

        except Exception as e:
            logger.error(
                f"Error processing webhook event {webhook_event.event_id}: {e}",
                extra={
                    "correlation_id": get_correlation_id(),
                    "event_id": webhook_event.event_id,
                },
            )
            webhook_event.status = WebhookEventStatus.FAILED
            webhook_event.error_message = str(e)
            webhook_event.retry_count += 1
            webhook_event.save()
            return False
