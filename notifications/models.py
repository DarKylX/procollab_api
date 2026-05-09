from django.conf import settings
from django.db import models


class Notification(models.Model):
    class Type(models.TextChoices):
        PROGRAM_SUBMITTED_TO_MODERATION = (
            "program_submitted_to_moderation",
            "Program submitted to moderation",
        )
        PROGRAM_MODERATION_APPROVED = (
            "program_moderation_approved",
            "Program moderation approved",
        )
        PROGRAM_MODERATION_REJECTED = (
            "program_moderation_rejected",
            "Program moderation rejected",
        )
        COMPANY_VERIFICATION_SUBMITTED = (
            "company_verification_submitted",
            "Company verification submitted",
        )
        COMPANY_VERIFICATION_APPROVED = (
            "company_verification_approved",
            "Company verification approved",
        )
        COMPANY_VERIFICATION_REJECTED = (
            "company_verification_rejected",
            "Company verification rejected",
        )
        EXPERT_PROJECTS_ASSIGNED = (
            "expert_projects_assigned",
            "Expert projects assigned",
        )

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    type = models.CharField(max_length=64, choices=Type.choices, db_index=True)
    title = models.CharField(max_length=255)
    message = models.TextField()
    object_type = models.CharField(max_length=64, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    url = models.CharField(max_length=500, blank=True)
    is_read = models.BooleanField(default=False, db_index=True)
    dedupe_key = models.CharField(max_length=255, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["recipient", "type", "dedupe_key"],
                name="unique_notification_per_recipient_event",
            )
        ]
        indexes = [
            models.Index(fields=["recipient", "is_read", "-created_at"]),
            models.Index(fields=["recipient", "type", "-created_at"]),
        ]

    def __str__(self):
        return f"Notification<{self.id}> {self.type} -> {self.recipient_id}"


class NotificationDelivery(models.Model):
    class Channel(models.TextChoices):
        IN_APP = "in_app", "In-app"
        EMAIL = "email", "Email"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        related_name="deliveries",
    )
    channel = models.CharField(max_length=16, choices=Channel.choices, db_index=True)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    error = models.TextField(blank=True)

    class Meta:
        ordering = ["-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["notification", "channel"],
                name="unique_notification_delivery_channel",
            )
        ]
        indexes = [
            models.Index(fields=["channel", "status"]),
        ]

    def __str__(self):
        return (
            f"NotificationDelivery<{self.id}> "
            f"{self.channel} {self.status} notification={self.notification_id}"
        )
