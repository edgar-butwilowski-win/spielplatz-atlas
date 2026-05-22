# Generated manually to align inspections choice labels with current models

from django.conf import settings
from django.db import migrations, models
from django.utils import timezone


class Migration(migrations.Migration):

    dependencies = [
        ("inspections", "0017_rename_inspection__organiz_3e0302_idx_inspections_organiz_e42d36_idx_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="inspectioncriterion",
            name="minimum_inspection_type",
            field=models.CharField(
                choices=[
                    ("visual", "Visual routine inspection"),
                    ("operational", "Operational inspection"),
                    ("annual", "Annual main inspection"),
                ],
                default="operational",
                help_text="Legt fest, ab welcher Kontrollart dieses Prüfkriterium berücksichtigt wird. Visuelle Kriterien erscheinen auch bei operativen und jährlichen Kontrollen.",
                max_length=30,
                verbose_name="Mindest-Kontrollart",
            ),
        ),
        migrations.AlterField(
            model_name="inspectioncriterionapplicability",
            name="scope_type",
            field=models.CharField(
                choices=[
                    ("playground", "General playground inspection"),
                    ("equipment", "Play equipment"),
                    ("surface", "Impact protection surface / ground"),
                    ("accessory", "Additional equipment"),
                ],
                max_length=30,
                verbose_name="Geltungsbereich",
            ),
        ),
        migrations.AlterField(
            model_name="inspection",
            name="inspection_type",
            field=models.CharField(
                choices=[
                    ("visual", "Visual routine inspection"),
                    ("operational", "Operational inspection"),
                    ("annual", "Annual main inspection"),
                ],
                default="visual",
                max_length=30,
                verbose_name="Kontrollart",
            ),
        ),
        migrations.AlterField(
            model_name="inspection",
            name="result",
            field=models.CharField(
                choices=[
                    ("ok", "OK"),
                    ("defects", "Defects found"),
                ],
                default="ok",
                max_length=30,
                verbose_name="Ergebnis",
            ),
        ),
        migrations.AlterField(
            model_name="inspection",
            name="status",
            field=models.CharField(
                choices=[
                    ("draft", "In progress"),
                    ("completed", "Completed"),
                ],
                default="draft",
                max_length=30,
                verbose_name="Status",
            ),
        ),
        migrations.AlterField(
            model_name="inspectiontask",
            name="inspection_type",
            field=models.CharField(
                choices=[
                    ("visual", "Visual routine inspection"),
                    ("operational", "Operational inspection"),
                    ("annual", "Annual main inspection"),
                ],
                max_length=30,
                verbose_name="Kontrollart",
            ),
        ),
        migrations.AlterField(
            model_name="inspectiontask",
            name="source",
            field=models.CharField(
                choices=[
                    ("automatic", "Automatic"),
                    ("manual", "Manual"),
                ],
                default="automatic",
                max_length=30,
                verbose_name="Quelle",
            ),
        ),
        migrations.AlterField(
            model_name="inspectiontask",
            name="status",
            field=models.CharField(
                choices=[
                    ("open", "Open"),
                    ("planned", "Planned"),
                    ("completed", "Done"),
                    ("overdue", "Overdue"),
                    ("suspended", "Suspended"),
                    ("cancelled", "Cancelled"),
                ],
                default="open",
                max_length=30,
                verbose_name="Status",
            ),
        ),
        migrations.AlterField(
            model_name="inspectionscope",
            name="scope_type",
            field=models.CharField(
                choices=[
                    ("playground", "General playground inspection"),
                    ("equipment", "Play equipment"),
                    ("surface", "Impact protection surface / ground"),
                    ("accessory", "Additional equipment"),
                ],
                max_length=30,
                verbose_name="Prüfbereich",
            ),
        ),
        migrations.AlterField(
            model_name="inspectionanswer",
            name="answer",
            field=models.CharField(
                choices=[
                    ("pending", "Not checked yet"),
                    ("ok", "OK"),
                    ("defect", "Defect"),
                    ("not_applicable", "Not applicable"),
                ],
                default="pending",
                max_length=30,
                verbose_name="Antwort",
            ),
        ),
        migrations.AlterField(
            model_name="defect",
            name="source_type",
            field=models.CharField(
                choices=[
                    ("inspection", "Inspection"),
                    ("citizen_report", "Citizen report"),
                    ("internal_report", "Internal report"),
                    ("maintenance", "Maintenance / care"),
                    ("other", "Other"),
                ],
                default="internal_report",
                max_length=30,
                verbose_name="Quelle",
            ),
        ),
        migrations.AlterField(
            model_name="defect",
            name="status",
            field=models.CharField(
                choices=[
                    ("open", "Open"),
                    ("in_progress", "In progress"),
                    ("planned", "Planned"),
                    ("done", "Resolved"),
                    ("verified", "Checked / completed"),
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
                    ("a_immediate", "A (immediate)"),
                    ("b_medium_term", "B (medium-term)"),
                ],
                help_text="Nur erfassen, wenn ein Sicherheitsrisiko besteht.",
                max_length=30,
                verbose_name="Dringlichkeit",
            ),
        ),
        migrations.AlterField(
            model_name="maintenanceaction",
            name="status",
            field=models.CharField(
                choices=[
                    ("planned", "Planned"),
                    ("in_progress", "In progress"),
                    ("done", "Completed"),
                    ("cancelled", "Cancelled"),
                ],
                default="planned",
                max_length=30,
                verbose_name="Status",
            ),
        ),
    ]
