# Generated manually to align translated inspection choice labels with current models

from django.db import migrations, models
from django.utils.translation import gettext_lazy as _


class Migration(migrations.Migration):

    dependencies = [
        ("inspections", "0018_align_choice_labels"),
    ]

    operations = [
        migrations.AlterField(
            model_name="inspectioncriterion",
            name="minimum_inspection_type",
            field=models.CharField(
                choices=[
                    ("visual", _("Visual routine inspection")),
                    ("operational", _("Operational inspection")),
                    ("annual", _("Annual main inspection")),
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
                    ("playground", _("General playground inspection")),
                    ("equipment", _("Play equipment")),
                    ("surface", _("Impact protection surface / ground")),
                    ("accessory", _("Additional equipment")),
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
                    ("visual", _("Visual routine inspection")),
                    ("operational", _("Operational inspection")),
                    ("annual", _("Annual main inspection")),
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
                    ("ok", _("OK")),
                    ("defects", _("Defects found")),
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
                    ("draft", _("In progress")),
                    ("completed", _("Completed")),
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
                    ("visual", _("Visual routine inspection")),
                    ("operational", _("Operational inspection")),
                    ("annual", _("Annual main inspection")),
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
                    ("automatic", _("Automatic")),
                    ("manual", _("Manual")),
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
                    ("open", _("Open")),
                    ("planned", _("Planned")),
                    ("completed", _("Done")),
                    ("overdue", _("Overdue")),
                    ("suspended", _("Suspended")),
                    ("cancelled", _("Cancelled")),
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
                    ("playground", _("General playground inspection")),
                    ("equipment", _("Play equipment")),
                    ("surface", _("Impact protection surface / ground")),
                    ("accessory", _("Additional equipment")),
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
                    ("pending", _("Not checked yet")),
                    ("ok", _("OK")),
                    ("defect", _("Defect")),
                    ("not_applicable", _("Not applicable")),
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
                    ("inspection", _("Inspection")),
                    ("citizen_report", _("Citizen report")),
                    ("internal_report", _("Internal report")),
                    ("maintenance", _("Maintenance / care")),
                    ("other", _("Other")),
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
                    ("open", _("Open")),
                    ("in_progress", _("In progress")),
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
    ]
