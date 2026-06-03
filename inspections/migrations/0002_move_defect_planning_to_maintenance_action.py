# Generated for moving defect planning data to MaintenanceAction

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def build_maintenance_title(defect):
    if getattr(defect, "equipment_id", None):
        return "Mangel beheben: Spielgerät"
    if getattr(defect, "surface_id", None):
        return "Mangel beheben: Fallschutzfläche"
    if getattr(defect, "accessory_id", None):
        return "Mangel beheben: Zusatzausstattung"
    return "Mangel beheben"


def migrate_planning_to_maintenance_actions(apps, schema_editor):
    Defect = apps.get_model("inspections", "Defect")
    MaintenanceAction = apps.get_model("inspections", "MaintenanceAction")
    DefectAssignment = apps.get_model("notifications", "DefectAssignment")

    assignments = {
        assignment.defect_id: assignment.assigned_to_id
        for assignment in DefectAssignment.objects.filter(assigned_to_id__isnull=False)
    }

    planned_defects = Defect.objects.filter(planned_resolution_date__isnull=False)
    for defect in planned_defects.iterator():
        action = (
            MaintenanceAction.objects
            .filter(defect_id=defect.id, status__in=["planned", "in_progress"])
            .order_by("planned_date", "-created_at")
            .first()
        )
        if action is None:
            action = MaintenanceAction(defect_id=defect.id, title=build_maintenance_title(defect), status="planned")
        if not action.title:
            action.title = build_maintenance_title(defect)
        action.planned_date = defect.planned_resolution_date
        action.assigned_to_id = assignments.get(defect.id)
        action.save()


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("inspections", "0001_initial"),
        ("notifications", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="maintenanceaction",
            name="assigned_to",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="assigned_maintenance_actions",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Zuständige Person",
            ),
        ),
        migrations.RunPython(migrate_planning_to_maintenance_actions, reverse_noop),
        migrations.RemoveField(
            model_name="defect",
            name="planned_resolution_date",
        ),
        migrations.AlterModelOptions(
            name="defect",
            options={"ordering": ["-has_safety_risk", "-created_at"], "verbose_name": "Mangel", "verbose_name_plural": "Mängel"},
        ),
    ]
