import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.utils.translation import gettext_lazy as _


class Migration(migrations.Migration):

    dependencies = [
        ("inspections", "0024_restore_inspection_task_reference_columns"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.RemoveField(
                    model_name="defect",
                    name="planned_resolution_date",
                ),
                migrations.AddField(
                    model_name="maintenanceaction",
                    name="assigned_to",
                    field=models.ForeignKey(
                        null=True,
                        blank=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="assigned_maintenance_actions",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Zuständige Person",
                    ),
                ),
                migrations.AddField(
                    model_name="inspectiontask",
                    name="generated_from_inspection",
                    field=models.ForeignKey(
                        null=True,
                        blank=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="generated_tasks",
                        to="inspections.inspection",
                        verbose_name="Aus Kontrolle erzeugt (alt)",
                    ),
                ),
                migrations.AlterField(
                    model_name="inspectiontask",
                    name="note",
                    field=models.TextField(blank=True, verbose_name="Interne Notiz"),
                ),
                migrations.AlterField(
                    model_name="inspectiontask",
                    name="created_from_inspection",
                    field=models.ForeignKey(
                        null=True,
                        blank=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="created_tasks",
                        to="inspections.inspection",
                        verbose_name="Aus Kontrolle erzeugt",
                    ),
                ),
                migrations.AlterField(
                    model_name="inspectiontask",
                    name="completed_by_inspection",
                    field=models.ForeignKey(
                        null=True,
                        blank=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="completed_tasks",
                        to="inspections.inspection",
                        verbose_name="Durch Kontrolle abgeschlossen",
                    ),
                ),
                migrations.AlterModelOptions(
                    name="defect",
                    options={
                        "ordering": ["-has_safety_risk", "-created_at"],
                        "verbose_name": "Mangel",
                        "verbose_name_plural": "Mängel",
                    },
                ),
                migrations.AlterField(
                    model_name="defect",
                    name="status",
                    field=models.CharField(
                        choices=[
                            ("open", _("Open")),
                            ("planned", _("Planned")),
                            ("done", _("Resolved")),
                            ("verified", _("Checked / completed")),
                        ],
                        default="open",
                        max_length=30,
                        verbose_name="Status",
                    ),
                ),
                migrations.AlterField(
                    model_name="defect",
                    name="urgency",
                    field=models.CharField(
                        blank=True,
                        choices=[
                            ("a_immediate", _("A (immediate)")),
                            ("b_medium_term", _("B (medium-term)")),
                        ],
                        help_text="Nur erfassen, wenn ein Sicherheitsrisiko besteht.",
                        max_length=30,
                        verbose_name="Dringlichkeit",
                    ),
                ),
                migrations.AlterModelOptions(
                    name="maintenanceaction",
                    options={
                        "ordering": ["planned_date", "-created_at"],
                        "verbose_name": "Instandhaltungsmassnahme",
                        "verbose_name_plural": "Instandhaltungsmassnahmen",
                    },
                ),
                migrations.AlterField(
                    model_name="maintenanceaction",
                    name="title",
                    field=models.CharField(max_length=255, verbose_name="Titel"),
                ),
                migrations.AlterField(
                    model_name="maintenanceaction",
                    name="description",
                    field=models.TextField(blank=True, verbose_name="Beschreibung"),
                ),
                migrations.AlterField(
                    model_name="maintenanceaction",
                    name="planned_date",
                    field=models.DateField(null=True, blank=True, verbose_name="Geplant am"),
                ),
                migrations.AlterField(
                    model_name="maintenanceaction",
                    name="completed_date",
                    field=models.DateField(null=True, blank=True, verbose_name="Abgeschlossen am"),
                ),
                migrations.AlterField(
                    model_name="maintenanceaction",
                    name="public_visible",
                    field=models.BooleanField(default=False, verbose_name="Öffentlich sichtbar"),
                ),
                migrations.AlterField(
                    model_name="maintenanceaction",
                    name="status",
                    field=models.CharField(
                        choices=[
                            ("planned", _("Planned")),
                            ("in_progress", _("In progress")),
                            ("done", _("Completed")),
                            ("cancelled", _("Cancelled")),
                        ],
                        default="planned",
                        max_length=30,
                        verbose_name="Status",
                    ),
                ),
            ],
        ),
    ]
