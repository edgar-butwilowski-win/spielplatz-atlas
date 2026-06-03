# Generated manually for defect status workflow cleanup.

from django.db import migrations, models


def migrate_in_progress_to_open(apps, schema_editor):
    Defect = apps.get_model("inspections", "Defect")
    Defect.objects.filter(status="in_progress").update(status="open")


def restore_open_to_in_progress(apps, schema_editor):
    # The old status cannot be restored reliably because open and in_progress are
    # intentionally merged by the forward migration.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("inspections", "0020_alter_inspectionrule_inspection_type"),
    ]

    operations = [
        migrations.RunPython(migrate_in_progress_to_open, restore_open_to_in_progress),
        migrations.AlterField(
            model_name="defect",
            name="status",
            field=models.CharField(
                choices=[
                    ("open", "Offen"),
                    ("planned", "Geplant"),
                    ("done", "Behoben"),
                    ("verified", "Geprüft / abgeschlossen"),
                ],
                default="open",
                max_length=30,
                verbose_name="Status",
            ),
        ),
    ]
