import uuid

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models

from certificates.enums import (
    CERTIFICATE_TYPE_CHOICES,
    CERTIFICATE_TYPE_PARTICIPATION,
    FONT_CHOICES,
    FONT_ROBOTO,
    ISSUE_CONDITION_CHOICES,
    ISSUE_CONDITION_SUBMITTED_PROJECT,
    RELEASE_MODE_AFTER_PROGRAM_END,
    RELEASE_MODE_CHOICES,
    get_default_fields_positioning,
)


hex_color_validator = RegexValidator(
    regex=r"^#[0-9A-Fa-f]{6}$",
    message="Color must be a HEX value in #RRGGBB format.",
)


def default_certificate_id():
    return f"CERT-LEGACY-{uuid.uuid4().hex[:12].upper()}"


def default_signature_position():
    return {"x": 0.60, "y": 0.79, "width": 0.16}


def default_stamp_position():
    return {"x": 0.43, "y": 0.80, "width": 0.13}


def default_company_logo_position():
    return {"x": 0.78, "y": 0.13, "width": 0.18}


class ProgramCertificateTemplate(models.Model):
    program = models.OneToOneField(
        "partner_programs.PartnerProgram",
        on_delete=models.CASCADE,
        related_name="certificate_template",
    )
    is_enabled = models.BooleanField(default=False, db_index=True)
    template_name = models.CharField(max_length=255, blank=True)
    background_image = models.ForeignKey(
        "files.UserFile",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="certificate_templates",
    )
    signature_image = models.ForeignKey(
        "files.UserFile",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="certificate_signature_templates",
    )
    stamp_image = models.ForeignKey(
        "files.UserFile",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="certificate_stamp_templates",
    )
    company_logo_image = models.ForeignKey(
        "files.UserFile",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="certificate_company_logo_templates",
    )
    signature_position = models.JSONField(default=default_signature_position, blank=True)
    stamp_position = models.JSONField(default=default_stamp_position, blank=True)
    company_logo_position = models.JSONField(
        default=default_company_logo_position,
        blank=True,
    )
    signer_name = models.CharField(max_length=255, blank=True, default="Анна Смирнова")
    font_family = models.CharField(
        max_length=32,
        choices=FONT_CHOICES,
        default=FONT_ROBOTO,
    )
    text_color = models.CharField(
        max_length=7,
        default="#1A1A1A",
        validators=[hex_color_validator],
    )
    accent_text_color = models.CharField(
        max_length=7,
        null=True,
        blank=True,
        validators=[hex_color_validator],
    )
    fields_positioning = models.JSONField(
        default=get_default_fields_positioning,
        blank=True,
    )
    issue_condition_type = models.CharField(
        max_length=32,
        choices=ISSUE_CONDITION_CHOICES,
        default=ISSUE_CONDITION_SUBMITTED_PROJECT,
    )
    release_mode = models.CharField(
        max_length=32,
        choices=RELEASE_MODE_CHOICES,
        default=RELEASE_MODE_AFTER_PROGRAM_END,
    )
    certificate_type = models.CharField(
        max_length=32,
        choices=CERTIFICATE_TYPE_CHOICES,
        default=CERTIFICATE_TYPE_PARTICIPATION,
    )
    show_project_title = models.BooleanField(default=True)
    show_team_members = models.BooleanField(default=False)
    show_rank = models.BooleanField(default=False)
    min_score = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
    )
    top_positions = models.PositiveIntegerField(null=True, blank=True)
    generated_at = models.DateTimeField(null=True, blank=True)
    released_at = models.DateTimeField(null=True, blank=True)
    datetime_created = models.DateTimeField(auto_now_add=True)
    datetime_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Program certificate template"
        verbose_name_plural = "Program certificate templates"
        ordering = ["-datetime_updated", "-id"]

    def __str__(self):
        return f"CertificateTemplate<{self.pk}> program={self.program_id}"


class CertificateGenerationRun(models.Model):
    STATUS_QUEUED = "queued"
    STATUS_RUNNING = "running"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_SKIPPED = "skipped"

    STATUS_CHOICES = [
        (STATUS_QUEUED, "Queued"),
        (STATUS_RUNNING, "Running"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_FAILED, "Failed"),
        (STATUS_SKIPPED, "Skipped"),
    ]

    program = models.ForeignKey(
        "partner_programs.PartnerProgram",
        on_delete=models.CASCADE,
        related_name="certificate_generation_runs",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_QUEUED,
        db_index=True,
    )
    total_expected = models.PositiveIntegerField(default=0)
    enqueued_count = models.PositiveIntegerField(default=0)
    issued_count = models.PositiveIntegerField(default=0)
    error_count = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)
    started_at = models.DateTimeField(auto_now_add=True, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    datetime_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Certificate generation run"
        verbose_name_plural = "Certificate generation runs"
        ordering = ["-started_at", "-id"]
        indexes = [
            models.Index(fields=["program", "-started_at"]),
            models.Index(fields=["status", "-started_at"]),
        ]

    def __str__(self):
        return f"CertificateGenerationRun<{self.pk}> program={self.program_id}"


class IssuedCertificate(models.Model):
    STATUS_GENERATED = "generated"
    STATUS_ERROR = "error"
    STATUS_REVOKED = "revoked"

    STATUS_CHOICES = [
        (STATUS_GENERATED, "Generated"),
        (STATUS_ERROR, "Error"),
        (STATUS_REVOKED, "Revoked"),
    ]

    program = models.ForeignKey(
        "partner_programs.PartnerProgram",
        on_delete=models.CASCADE,
        related_name="issued_certificates",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="issued_certificates",
    )
    program_project = models.ForeignKey(
        "partner_programs.PartnerProgramProject",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="issued_certificates",
    )
    certificate_id = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        default=default_certificate_id,
    )
    team_name = models.CharField(max_length=255, blank=True)
    final_score = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
    )
    rating_position = models.PositiveIntegerField(null=True, blank=True)
    certificate_uuid = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    pdf_file = models.ForeignKey(
        "files.UserFile",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="issued_certificates",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_GENERATED,
        db_index=True,
    )
    generated_at = models.DateTimeField(null=True, blank=True, db_index=True)
    downloaded_at = models.DateTimeField(null=True, blank=True)
    issued_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Issued certificate"
        verbose_name_plural = "Issued certificates"
        ordering = ["-issued_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["program", "user", "program_project"],
                condition=~models.Q(status="revoked"),
                name="uniq_active_certificate_program_user_project",
            )
        ]
        indexes = [
            models.Index(
                fields=["program", "user", "program_project"],
                name="certificate_program_0f7a73_idx",
            ),
            models.Index(fields=["certificate_uuid"]),
            models.Index(fields=["certificate_id"], name="certificate_certifi_aa2a35_idx"),
        ]

    def __str__(self):
        return (
            f"IssuedCertificate<{self.pk}> "
            f"program={self.program_id} user={self.user_id}"
        )
