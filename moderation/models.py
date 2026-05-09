from django.conf import settings
from django.db import models


class ModerationLog(models.Model):
    ACTION_VERIFICATION_SUBMITTED = "verification_submitted"
    ACTION_VERIFICATION_APPROVE = "verification_approve"
    ACTION_VERIFICATION_REJECT = "verification_reject"
    ACTION_VERIFICATION_REVOKE = "verification_revoke"

    ACTION_CHOICES = [
        (ACTION_VERIFICATION_SUBMITTED, "Verification submitted"),
        (ACTION_VERIFICATION_APPROVE, "Verification approve"),
        (ACTION_VERIFICATION_REJECT, "Verification reject"),
        (ACTION_VERIFICATION_REVOKE, "Verification revoke"),
    ]

    program = models.ForeignKey(
        "partner_programs.PartnerProgram",
        on_delete=models.CASCADE,
        related_name="moderation_logs",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="moderation_logs",
    )
    action = models.CharField(
        max_length=40,
        choices=ACTION_CHOICES,
        db_index=True,
    )
    status_before = models.CharField(max_length=20, blank=True)
    status_after = models.CharField(max_length=20, blank=True)
    comment = models.TextField(blank=True)
    rejection_reason = models.CharField(max_length=40, blank=True)
    datetime_created = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Moderation log"
        verbose_name_plural = "Moderation logs"
        ordering = ["-datetime_created", "-id"]
        indexes = [
            models.Index(fields=["program", "action", "-datetime_created"]),
        ]

    def __str__(self):
        return f"{self.get_action_display()} - {self.program_id}"
