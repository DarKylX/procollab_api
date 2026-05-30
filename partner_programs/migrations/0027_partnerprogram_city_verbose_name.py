from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("partner_programs", "0026_russian_choice_labels"),
    ]

    operations = [
        migrations.AlterField(
            model_name="partnerprogram",
            name="city",
            field=models.TextField(verbose_name="Формат проведения"),
        ),
    ]
