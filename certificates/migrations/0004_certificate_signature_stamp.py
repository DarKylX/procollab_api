from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("files", "0007_auto_20230929_1727"),
        ("certificates", "0003_certificate_mvp_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="programcertificatetemplate",
            name="signature_image",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="certificate_signature_templates",
                to="files.userfile",
            ),
        ),
        migrations.AddField(
            model_name="programcertificatetemplate",
            name="stamp_image",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="certificate_stamp_templates",
                to="files.userfile",
            ),
        ),
    ]
