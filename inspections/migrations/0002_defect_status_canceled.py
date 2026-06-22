# Generated manually for SpielplatzAtlas.

from django.db import migrations, models
from django.utils.translation import gettext_lazy as _


class Migration(migrations.Migration):

    dependencies = [
        ("inspections", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="defect",
            name="status",
            field=models.CharField(
                choices=[
                    ("open", _("Open")),
                    ("planned", _("Planned")),
                    ("done", _("Resolved")),
                    ("verified", _("Checked / completed")),
                    ("canceled", _("Canceled")),
                ],
                default="open",
                max_length=30,
                verbose_name="Status",
            ),
        ),
    ]
