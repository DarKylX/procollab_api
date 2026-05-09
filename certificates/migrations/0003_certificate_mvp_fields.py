from django.db import migrations, models
import django.db.models.deletion
import certificates.models


def populate_certificate_ids(apps, schema_editor):
    IssuedCertificate = apps.get_model("certificates", "IssuedCertificate")
    seen = set()
    for index, certificate in enumerate(
        IssuedCertificate.objects.order_by("program_id", "user_id", "id"), start=1
    ):
        sequence = index
        candidate = f"CERT-{certificate.program_id}-{certificate.user_id}-{sequence:06d}"
        while candidate in seen or IssuedCertificate.objects.filter(
            certificate_id=candidate
        ).exclude(pk=certificate.pk).exists():
            sequence += 1
            candidate = f"CERT-{certificate.program_id}-{certificate.user_id}-{sequence:06d}"

        certificate.certificate_id = candidate
        certificate.generated_at = certificate.issued_at
        certificate.status = "generated"
        certificate.save(
            update_fields=["certificate_id", "generated_at", "status"]
        )
        seen.add(candidate)


class Migration(migrations.Migration):

    dependencies = [
        ("certificates", "0002_certificategenerationrun_issuedcertificate_and_more"),
        ("partner_programs", "0021_partnerprogram_verification_status_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="programcertificatetemplate",
            name="certificate_type",
            field=models.CharField(
                choices=[("participation", "Participation certificate")],
                default="participation",
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="programcertificatetemplate",
            name="generated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="programcertificatetemplate",
            name="is_enabled",
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name="programcertificatetemplate",
            name="release_mode",
            field=models.CharField(
                choices=[
                    ("after_program_end", "After program end"),
                    ("manual", "Manual"),
                ],
                default="after_program_end",
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="programcertificatetemplate",
            name="released_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="programcertificatetemplate",
            name="show_project_title",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="programcertificatetemplate",
            name="show_rank",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="programcertificatetemplate",
            name="show_team_members",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="programcertificatetemplate",
            name="template_name",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AlterField(
            model_name="programcertificatetemplate",
            name="issue_condition_type",
            field=models.CharField(
                choices=[
                    ("all_registered", "All registered participants"),
                    ("submitted_project", "Participants with submitted projects"),
                    ("score_threshold", "Participants with score above threshold"),
                    ("top_positions", "Prize positions"),
                ],
                default="submitted_project",
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="certificategenerationrun",
            name="error_count",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.RemoveConstraint(
            model_name="issuedcertificate",
            name="uniq_issued_certificate_program_user",
        ),
        migrations.RemoveIndex(
            model_name="issuedcertificate",
            name="certificate_program_70a5d9_idx",
        ),
        migrations.AddField(
            model_name="issuedcertificate",
            name="certificate_id",
            field=models.CharField(
                blank=True,
                db_index=True,
                max_length=64,
                null=True,
                unique=True,
            ),
        ),
        migrations.AddField(
            model_name="issuedcertificate",
            name="downloaded_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="issuedcertificate",
            name="generated_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="issuedcertificate",
            name="program_project",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="issued_certificates",
                to="partner_programs.partnerprogramproject",
            ),
        ),
        migrations.AddField(
            model_name="issuedcertificate",
            name="status",
            field=models.CharField(
                choices=[
                    ("generated", "Generated"),
                    ("error", "Error"),
                    ("revoked", "Revoked"),
                ],
                db_index=True,
                default="generated",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="issuedcertificate",
            name="pdf_file",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="issued_certificates",
                to="files.userfile",
            ),
        ),
        migrations.RunPython(populate_certificate_ids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="issuedcertificate",
            name="certificate_id",
            field=models.CharField(
                db_index=True,
                default=certificates.models.default_certificate_id,
                max_length=64,
                unique=True,
            ),
        ),
        migrations.AddConstraint(
            model_name="issuedcertificate",
            constraint=models.UniqueConstraint(
                condition=~models.Q(status="revoked"),
                fields=("program", "user", "program_project"),
                name="uniq_active_certificate_program_user_project",
            ),
        ),
        migrations.AddIndex(
            model_name="issuedcertificate",
            index=models.Index(
                fields=["program", "user", "program_project"],
                name="certificate_program_0f7a73_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="issuedcertificate",
            index=models.Index(
                fields=["certificate_id"], name="certificate_certifi_aa2a35_idx"
            ),
        ),
    ]
