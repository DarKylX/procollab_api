# Generated for the core case championship PR.

from django.db import migrations


def migrate_draft_to_status(apps, schema_editor):
    PartnerProgram = apps.get_model("partner_programs", "PartnerProgram")
    PartnerProgram.objects.filter(draft=True).update(status="draft")
    PartnerProgram.objects.filter(draft=False).update(status="published")


def reverse_migrate(apps, schema_editor):
    PartnerProgram = apps.get_model("partner_programs", "PartnerProgram")
    PartnerProgram.objects.filter(status="draft").update(draft=True)
    PartnerProgram.objects.exclude(status="draft").update(draft=False)


class Migration(migrations.Migration):
    dependencies = [
        ("partner_programs", "0017_partnerprogram_status_company"),
    ]

    operations = [
        migrations.RunPython(migrate_draft_to_status, reverse_migrate),
    ]
