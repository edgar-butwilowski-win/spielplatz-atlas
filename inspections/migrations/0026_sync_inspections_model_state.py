import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Migration(migrations.Migration):

    dependencies = [
        ("inspections", "0025_align_state_with_current_models"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AlterModelOptions(
                    name="inspectiontask",
                    options={
                        "ordering": ["due_date", "playground__name", "inspection_type"],
                        "verbose_name": "Kontrollauftrag",
                        "verbose_name_plural": "Kontrollaufträge",
                    },
                ),
                migrations.AddIndex(
                    model_name="inspectiontask",
                    index=models.Index(fields=["organization", "due_date", "status"], name="inspection__organiz_b5f749_idx"),
                ),
                migrations.AddIndex(
                    model_name="inspectiontask",
                    index=models.Index(fields=["playground", "inspection_type", "due_date"], name="inspection__playgro_9afc9d_idx"),
                ),
                migrations.AlterField(
                    model_name="inspectiontask",
                    name="organization",
                    field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="inspection_tasks", to="tenants.organization", verbose_name="Organisation"),
                ),
                migrations.AlterField(
                    model_name="inspectiontask",
                    name="playground",
                    field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="inspection_tasks", to="playgrounds.playground", verbose_name="Spielplatz"),
                ),
                migrations.AlterField(
                    model_name="inspectiontask",
                    name="inspection_type",
                    field=models.CharField(choices=[("visual", _("Visual routine inspection")), ("operational", _("Operational inspection")), ("annual", _("Annual main inspection"))], max_length=30, verbose_name="Kontrollart"),
                ),
                migrations.AlterField(
                    model_name="inspectiontask",
                    name="due_date",
                    field=models.DateField(verbose_name="Fällig am"),
                ),
                migrations.AlterField(
                    model_name="inspectiontask",
                    name="planned_date",
                    field=models.DateField(blank=True, null=True, verbose_name="Geplant am"),
                ),
                migrations.AlterField(
                    model_name="inspectiontask",
                    name="assigned_to",
                    field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="assigned_inspection_tasks", to=settings.AUTH_USER_MODEL, verbose_name="Zuständige Person"),
                ),
                migrations.AlterField(
                    model_name="inspectiontask",
                    name="status",
                    field=models.CharField(choices=[("open", _("Open")), ("planned", _("Planned")), ("completed", _("Done")), ("overdue", _("Overdue")), ("suspended", _("Suspended")), ("cancelled", _("Cancelled"))], default="open", max_length=30, verbose_name="Status"),
                ),
                migrations.AlterField(
                    model_name="inspectiontask",
                    name="source",
                    field=models.CharField(choices=[("automatic", _("Automatic")), ("manual", _("Manual"))], default="automatic", max_length=30, verbose_name="Quelle"),
                ),
                migrations.AlterField(
                    model_name="inspectiontask",
                    name="note",
                    field=models.TextField(blank=True, verbose_name="Interne Notiz"),
                ),
                migrations.AlterField(
                    model_name="inspectiontask",
                    name="created_from_inspection",
                    field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_tasks", to="inspections.inspection", verbose_name="Aus Kontrolle erzeugt"),
                ),
                migrations.AlterField(
                    model_name="inspectiontask",
                    name="completed_by_inspection",
                    field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="completed_tasks", to="inspections.inspection", verbose_name="Durch Kontrolle abgeschlossen"),
                ),
                migrations.AlterField(
                    model_name="inspectiontask",
                    name="generated_from_inspection",
                    field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="generated_tasks", to="inspections.inspection", verbose_name="Aus Kontrolle erzeugt (alt)"),
                ),
                migrations.AlterField(
                    model_name="inspectiontask",
                    name="created_at",
                    field=models.DateTimeField(auto_now_add=True, verbose_name="Erstellt am"),
                ),
                migrations.AlterField(
                    model_name="inspectiontask",
                    name="updated_at",
                    field=models.DateTimeField(auto_now=True, verbose_name="Aktualisiert am"),
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
                    name="defect",
                    field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="maintenance_actions", to="inspections.defect", verbose_name="Mangel"),
                ),
                migrations.AlterField(
                    model_name="maintenanceaction",
                    name="assigned_to",
                    field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="assigned_maintenance_actions", to=settings.AUTH_USER_MODEL, verbose_name="Zuständige Person"),
                ),
                migrations.AlterField(
                    model_name="maintenanceaction",
                    name="created_at",
                    field=models.DateTimeField(auto_now_add=True, verbose_name="Erstellt am"),
                ),
                migrations.AlterField(
                    model_name="maintenanceaction",
                    name="updated_at",
                    field=models.DateTimeField(auto_now=True, verbose_name="Aktualisiert am"),
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
                    field=models.CharField(choices=[("open", _("Open")), ("planned", _("Planned")), ("done", _("Resolved")), ("verified", _("Checked / completed"))], default="open", max_length=30, verbose_name="Status"),
                ),
                migrations.AlterField(
                    model_name="defect",
                    name="urgency",
                    field=models.CharField(blank=True, choices=[("a_immediate", _("A (immediate)")), ("b_medium_term", _("B (medium-term)"))], help_text="Nur erfassen, wenn ein Sicherheitsrisiko besteht.", max_length=30, verbose_name="Dringlichkeit"),
                ),
                migrations.AlterField(
                    model_name="defect",
                    name="updated_at",
                    field=models.DateTimeField(auto_now=True, verbose_name="Aktualisiert am"),
                ),
                migrations.AlterField(
                    model_name="defect",
                    name="created_at",
                    field=models.DateTimeField(auto_now_add=True, verbose_name="Erstellt am"),
                ),
            ],
        ),
    ]
