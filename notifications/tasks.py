import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template import TemplateDoesNotExist
from django.template.loader import render_to_string
from django.utils import timezone

from notifications.models import NotificationDelivery
from procollab.celery import app

logger = logging.getLogger(__name__)


@app.task(name="notifications.tasks.send_notification_email")
def send_notification_email(
    delivery_id: int,
    subject: str,
    template_name: str,
    context: dict,
    plain_text: str,
) -> bool:
    try:
        delivery = NotificationDelivery.objects.select_related(
            "notification__recipient"
        ).get(pk=delivery_id)
    except NotificationDelivery.DoesNotExist:
        logger.warning("NotificationDelivery %s does not exist", delivery_id)
        return False

    if delivery.status == NotificationDelivery.Status.SENT:
        return True

    recipient = delivery.notification.recipient
    if not recipient.email:
        delivery.status = NotificationDelivery.Status.FAILED
        delivery.error = "recipient email is empty"
        delivery.save(update_fields=["status", "error"])
        return False

    html_message = None
    try:
        html_message = render_to_string(template_name, context)
    except TemplateDoesNotExist:
        logger.warning("Email template %s is missing; using plain text", template_name)
    except Exception as exc:
        logger.exception("Email template %s render failed", template_name)
        delivery.error = f"html render failed; plain text fallback used: {exc}"

    try:
        message = EmailMultiAlternatives(
            subject=subject,
            body=plain_text,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", settings.EMAIL_USER),
            to=[recipient.email],
        )
        if html_message:
            message.attach_alternative(html_message, "text/html")
        sent_count = message.send(fail_silently=False)
    except Exception as exc:
        delivery.status = NotificationDelivery.Status.FAILED
        delivery.error = str(exc)
        delivery.save(update_fields=["status", "error"])
        logger.exception("Notification email delivery %s failed", delivery_id)
        return False

    if sent_count:
        delivery.status = NotificationDelivery.Status.SENT
        delivery.sent_at = timezone.now()
        delivery.error = delivery.error or ""
        delivery.save(update_fields=["status", "sent_at", "error"])
        return True

    delivery.status = NotificationDelivery.Status.FAILED
    delivery.error = "email backend returned 0 sent messages"
    delivery.save(update_fields=["status", "error"])
    return False
