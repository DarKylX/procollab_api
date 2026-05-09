from django.db import migrations, models
import django.db.models.deletion

import certificates.models


OLD_SIGNATURE_POSITION = {"x": 0.72, "y": 0.77, "width": 0.18}
NEW_SIGNATURE_POSITION = {"x": 0.60, "y": 0.79, "width": 0.16}
OLD_SIGNER_FIELD = {
    "x": 0.69,
    "y": 0.83,
    "font_size": 15,
    "align": "left",
    "visible": True,
    "color": None,
}
NEW_SIGNER_FIELD = {
    "x": 0.60,
    "y": 0.88,
    "font_size": 15,
    "align": "left",
    "visible": True,
    "color": None,
}


def update_saved_defaults(apps, schema_editor):
    template_model = apps.get_model("certificates", "ProgramCertificateTemplate")
    for template in template_model.objects.all():
        update_fields = []
        if template.signature_position == OLD_SIGNATURE_POSITION:
            template.signature_position = NEW_SIGNATURE_POSITION
            update_fields.append("signature_position")

        fields_positioning = template.fields_positioning or {}
        if fields_positioning.get("signer_name") == OLD_SIGNER_FIELD:
            fields_positioning["signer_name"] = NEW_SIGNER_FIELD
            template.fields_positioning = fields_positioning
            update_fields.append("fields_positioning")

        if update_fields:
            template.save(update_fields=update_fields)


class Migration(migrations.Migration):
    dependencies = [
        ("files", "0007_auto_20230929_1727"),
        ("certificates", "0005_certificate_asset_layout_signer"),
    ]

    operations = [
        migrations.AddField(
            model_name="programcertificatetemplate",
            name="company_logo_image",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="certificate_company_logo_templates",
                to="files.userfile",
            ),
        ),
        migrations.AddField(
            model_name="programcertificatetemplate",
            name="company_logo_position",
            field=models.JSONField(
                blank=True,
                default=certificates.models.default_company_logo_position,
            ),
        ),
        migrations.AlterField(
            model_name="programcertificatetemplate",
            name="signature_position",
            field=models.JSONField(
                blank=True,
                default=certificates.models.default_signature_position,
            ),
        ),
        migrations.RunPython(update_saved_defaults, migrations.RunPython.noop),
    ]
