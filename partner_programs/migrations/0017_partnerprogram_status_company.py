# Generated for the core case championship PR.

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("projects", "0032_hide_program_projects"),
        ("partner_programs", "0016_partnerprogram_is_distributed_evaluation"),
    ]

    operations = [
        migrations.AddField(
            model_name="partnerprogram",
            name="status",
            field=models.CharField(
                choices=[
                    ("draft", "Draft"),
                    ("published", "Published"),
                    ("completed", "Completed"),
                    ("archived", "Archived"),
                ],
                db_index=True,
                default="draft",
                max_length=20,
                verbose_name="Program status",
            ),
        ),
        migrations.AddField(
            model_name="partnerprogram",
            name="company",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="programs",
                to="projects.company",
                verbose_name="Organizer company",
            ),
        ),
        migrations.AlterField(
            model_name="partnerprogram",
            name="draft",
            field=models.BooleanField(
                default=True,
                help_text="Legacy flag kept for backward compatibility; use status instead.",
                verbose_name="[DEPRECATED] Draft",
            ),
        ),
    ]
