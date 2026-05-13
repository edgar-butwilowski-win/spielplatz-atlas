# Generated manually for SpielplatzAtlas

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inspections", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="defect",
            name="urgency",
            field=models.CharField(
                blank=True,
                choices=[
                    ("a_immediate", "A (sofort)"),
                    ("b_medium_term", "B (mittelfristig)"),
                ],
                help_text="Nur erfassen, wenn ein Sicherheitsrisiko besteht.",
                max_length=30,
                verbose_name="Dringlichkeit",
            ),
        ),
    ]
