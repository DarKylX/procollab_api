from django.db import migrations, models

import certificates.models


class Migration(migrations.Migration):
    dependencies = [
        ("certificates", "0004_certificate_signature_stamp"),
    ]

    operations = [
        migrations.AddField(
            model_name="programcertificatetemplate",
            name="signature_position",
            field=models.JSONField(
                blank=True,
                default=certificates.models.default_signature_position,
            ),
        ),
        migrations.AddField(
            model_name="programcertificatetemplate",
            name="stamp_position",
            field=models.JSONField(
                blank=True,
                default=certificates.models.default_stamp_position,
            ),
        ),
        migrations.AddField(
            model_name="programcertificatetemplate",
            name="signer_name",
            field=models.CharField(blank=True, default="Анна Смирнова", max_length=255),
        ),
    ]
