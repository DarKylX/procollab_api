from django.contrib import admin

from certificates.models import (
    CertificateGenerationRun,
    IssuedCertificate,
    ProgramCertificateTemplate,
)


@admin.register(ProgramCertificateTemplate)
class ProgramCertificateTemplateAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "program",
        "is_enabled",
        "release_mode",
        "font_family",
        "issue_condition_type",
        "background_image",
        "signature_image",
        "stamp_image",
        "company_logo_image",
        "signer_name",
        "generated_at",
        "released_at",
        "datetime_created",
        "datetime_updated",
    )
    list_filter = (
        "is_enabled",
        "release_mode",
        "font_family",
        "issue_condition_type",
        "datetime_created",
    )
    search_fields = ("program__name",)
    raw_id_fields = (
        "program",
        "background_image",
        "signature_image",
        "stamp_image",
        "company_logo_image",
    )


@admin.register(IssuedCertificate)
class IssuedCertificateAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "program",
        "user",
        "program_project",
        "certificate_id",
        "status",
        "certificate_uuid",
        "final_score",
        "rating_position",
        "generated_at",
        "downloaded_at",
        "issued_at",
    )
    list_filter = ("status", "generated_at", "issued_at")
    search_fields = (
        "program__name",
        "user__email",
        "certificate_id",
        "certificate_uuid",
    )
    raw_id_fields = ("program", "user", "program_project", "pdf_file")


@admin.register(CertificateGenerationRun)
class CertificateGenerationRunAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "program",
        "status",
        "total_expected",
        "enqueued_count",
        "issued_count",
        "error_count",
        "started_at",
        "completed_at",
    )
    list_filter = ("status", "started_at")
    search_fields = ("program__name", "error_message")
    raw_id_fields = ("program",)
