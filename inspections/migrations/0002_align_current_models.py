# Generated manually to align inspections models with current code

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.utils import timezone


class Migration(migrations.Migration):

    dependencies = [
        ("inspections", "0001_initial"),
        ("playgrounds", "0013_spatialite_geometry"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="inspectioncriterion",
            name="norm_reference",
            field=models.CharField(blank=True, max_length=255, verbose_name="Norm-/Quellenhinweis"),
        ),
        migrations.AddField(
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
        migrations.AddField(
            model_name="inspectioncriterion",
            name="is_standard",
            field=models.BooleanField(default=False, verbose_name="Standardkriterium"),
        ),
        migrations.AddField(
            model_name="inspectioncriterion",
            name="standard_version",
            field=models.CharField(blank=True, max_length=100, verbose_name="Standardversion"),
        ),
        migrations.AddField(
            model_name="inspectioncriterion",
            name="source_note",
            field=models.TextField(blank=True, verbose_name="Quellen-/Bearbeitungshinweis"),
        ),
        migrations.AddField(
            model_name="inspectioncriterion",
            name="is_locked",
            field=models.BooleanField(default=False, help_text="Gesperrte globale Standards dürfen durch Organisationen nicht verändert werden.", verbose_name="Gesperrt"),
        ),
        migrations.AddField(
            model_name="inspectioncriterion",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, default=timezone.now, verbose_name="Erstellt am"),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="inspectioncriterion",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, default=timezone.now, verbose_name="Aktualisiert am"),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="inspectioncriterion",
            name="area",
            field=models.CharField(blank=True, max_length=255, verbose_name="Bereich"),
        ),
        migrations.AlterField(
            model_name="inspectioncriterion",
            name="title",
            field=models.CharField(max_length=255, verbose_name="Titel"),
        ),
        migrations.AlterField(
            model_name="inspectioncriterion",
            name="inspection_text",
            field=models.TextField(blank=True, verbose_name="Prüfhinweis"),
        ),
        migrations.AlterField(
            model_name="inspectioncriterion",
            name="maintenance_text",
            field=models.TextField(blank=True, verbose_name="Wartungshinweis"),
        ),
        migrations.AlterField(
            model_name="inspectioncriterion",
            name="is_active",
            field=models.BooleanField(default=True, verbose_name="Aktiv"),
        ),
        migrations.AlterField(
            model_name="inspectioncriterion",
            name="organization",
            field=models.ForeignKey(blank=True, help_text="Leer lassen für globale Anbieter-Standards.", null=True, on_delete=django.db.models.deletion.CASCADE, related_name="inspection_criteria", to="tenants.organization", verbose_name="Organisation"),
        ),
        migrations.CreateModel(
            name="InspectionCriterionApplicability",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("scope_type", models.CharField(choices=[("playground", "General playground inspection"), ("equipment", "Play equipment"), ("surface", "Impact protection surface / ground"), ("accessory", "Additional equipment")], max_length=30, verbose_name="Geltungsbereich")),
                ("applies_to_all_equipment", models.BooleanField(default=False, help_text="Nur relevant, wenn der Geltungsbereich «Spielgerät» ist.", verbose_name="Gilt für alle Spielgerätearten")),
                ("criterion", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="applicabilities", to="inspections.inspectioncriterion", verbose_name="Prüfkriterium")),
                ("equipment_types", models.ManyToManyField(blank=True, help_text="Nur relevant, wenn der Geltungsbereich «Spielgerät» ist und das Prüfkriterium nicht für alle Spielgerätearten gilt.", related_name="criterion_applicabilities", to="playgrounds.equipmenttype", verbose_name="Nur für diese Spielgerätearten")),
            ],
            options={
                "verbose_name": "Anwendbarkeit",
                "verbose_name_plural": "Anwendbarkeiten",
                "ordering": ["criterion__area", "criterion__title", "scope_type"],
                "unique_together": {("criterion", "scope_type")},
            },
        ),
        migrations.AlterField(
            model_name="inspection",
            name="inspection_type",
            field=models.CharField(choices=[("visual", "Visual routine inspection"), ("operational", "Operational inspection"), ("annual", "Annual main inspection")], default="visual", max_length=30, verbose_name="Kontrollart"),
        ),
        migrations.AlterField(
            model_name="inspection",
            name="inspected_at",
            field=models.DateField(default=timezone.localdate, verbose_name="Kontrolldatum"),
        ),
        migrations.AlterField(
            model_name="inspection",
            name="inspector",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="inspections", to=settings.AUTH_USER_MODEL, verbose_name="Kontrollperson"),
        ),
        migrations.AlterField(
            model_name="inspection",
            name="result",
            field=models.CharField(choices=[("ok", "OK"), ("defects", "Defects found")], default="ok", max_length=30, verbose_name="Ergebnis"),
        ),
        migrations.AddField(
            model_name="inspection",
            name="status",
            field=models.CharField(choices=[("draft", "In progress"), ("completed", "Completed")], default="draft", max_length=30, verbose_name="Status"),
        ),
        migrations.AddField(
            model_name="inspection",
            name="completed_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="Abgeschlossen am"),
        ),
        migrations.AddField(
            model_name="inspection",
            name="completed_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="completed_inspections", to=settings.AUTH_USER_MODEL, verbose_name="Abgeschlossen durch"),
        ),
        migrations.CreateModel(
            name="InspectionRule",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("inspection_type", models.CharField(choices=[("visual", "Visual routine inspection"), ("operational", "Operational inspection"), ("annual", "Annual main inspection")], max_length=30, verbose_name="Kontrollart")),
                ("interval_days", models.PositiveIntegerField(help_text="Intervall für die Kontrollplanung auf Basis von SN EN 1176/1177.", verbose_name="Intervall in Tagen")),
                ("applies_to_all_playgrounds", models.BooleanField(default=True, verbose_name="Gilt für alle Spielplätze")),
                ("is_active", models.BooleanField(default=True, verbose_name="Aktiv")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Erstellt am")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Aktualisiert am")),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="inspection_rules", to="tenants.organization", verbose_name="Organisation")),
            ],
            options={
                "verbose_name": "Kontrollregel",
                "verbose_name_plural": "Kontrollregeln",
                "ordering": ["organization__name", "inspection_type"],
                "unique_together": {("organization", "inspection_type")},
            },
        ),
        migrations.CreateModel(
            name="InspectionTask",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("inspection_type", models.CharField(choices=[("visual", "Visual routine inspection"), ("operational", "Operational inspection"), ("annual", "Annual main inspection")], max_length=30, verbose_name="Kontrollart")),
                ("due_date", models.DateField(verbose_name="Fällig am")),
                ("planned_date", models.DateField(blank=True, null=True, verbose_name="Geplant am")),
                ("status", models.CharField(choices=[("open", "Open"), ("planned", "Planned"), ("completed", "Done"), ("overdue", "Overdue"), ("suspended", "Suspended"), ("cancelled", "Cancelled")], default="open", max_length=30, verbose_name="Status")),
                ("source", models.CharField(choices=[("automatic", "Automatic"), ("manual", "Manual")], default="automatic", max_length=30, verbose_name="Quelle")),
                ("note", models.TextField(blank=True, verbose_name="Interne Bemerkung")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Erstellt am")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Aktualisiert am")),
                ("assigned_to", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="assigned_inspection_tasks", to=settings.AUTH_USER_MODEL, verbose_name="Zugewiesen an")),
                ("completed_by_inspection", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="completed_planning_tasks", to="inspections.inspection", verbose_name="Erledigt durch Kontrolle")),
                ("created_from_inspection", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_follow_up_tasks", to="inspections.inspection", verbose_name="Erzeugt aus Kontrolle")),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="inspection_tasks", to="tenants.organization", verbose_name="Organisation")),
                ("playground", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="inspection_tasks", to="playgrounds.playground", verbose_name="Spielplatz")),
            ],
            options={
                "verbose_name": "Kontrollauftrag",
                "verbose_name_plural": "Kontrollaufträge",
                "ordering": ["due_date", "planned_date", "playground__name"],
                "indexes": [models.Index(fields=["organization", "status", "due_date"], name="inspection__organiz_0dfd0a_idx"), models.Index(fields=["playground", "inspection_type", "status"], name="inspection__playgro_d561c7_idx")],
            },
        ),
        migrations.CreateModel(
            name="InspectionScope",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("scope_type", models.CharField(choices=[("playground", "General playground inspection"), ("equipment", "Play equipment"), ("surface", "Impact protection surface / ground"), ("accessory", "Additional equipment")], max_length=30, verbose_name="Prüfbereich")),
                ("label", models.CharField(max_length=255, verbose_name="Bezeichnung")),
                ("sort_order", models.PositiveIntegerField(default=0, verbose_name="Sortierung")),
                ("accessory", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="inspection_scopes", to="playgrounds.playgroundaccessory", verbose_name="Zusatzausstattung")),
                ("equipment", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="inspection_scopes", to="playgrounds.playequipment", verbose_name="Spielgerät")),
                ("inspection", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="scopes", to="inspections.inspection", verbose_name="Kontrolle")),
                ("surface", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="inspection_scopes", to="playgrounds.playgroundsurface", verbose_name="Fallschutzfläche / Boden")),
            ],
            options={
                "verbose_name": "Prüfbereich",
                "verbose_name_plural": "Prüfbereiche",
                "ordering": ["sort_order", "label"],
            },
        ),
        migrations.AddField(
            model_name="inspectionanswer",
            name="scope",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="answers", to="inspections.inspectionscope", verbose_name="Prüfbereich"),
        ),
        migrations.AddField(
            model_name="inspectionanswer",
            name="equipment",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="inspection_answers", to="playgrounds.playequipment", verbose_name="Spielgerät"),
        ),
        migrations.AddField(
            model_name="inspectionanswer",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, default=timezone.now, verbose_name="Erstellt am"),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="inspectionanswer",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, default=timezone.now, verbose_name="Aktualisiert am"),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="inspectionanswer",
            name="answer",
            field=models.CharField(choices=[("pending", "Not checked yet"), ("ok", "OK"), ("defect", "Defect"), ("not_applicable", "Not applicable")], default="pending", max_length=30, verbose_name="Antwort"),
        ),
        migrations.AlterUniqueTogether(
            name="inspectionanswer",
            unique_together={("inspection", "scope", "criterion")},
        ),
        migrations.AddField(
            model_name="defect",
            name="inspection_answer",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="defects", to="inspections.inspectionanswer", verbose_name="Prüfantwort"),
        ),
        migrations.AddField(
            model_name="defect",
            name="playground",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="defects", to="playgrounds.playground", verbose_name="Spielplatz"),
        ),
        migrations.AddField(
            model_name="defect",
            name="surface",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="defects", to="playgrounds.playgroundsurface", verbose_name="Fallschutzfläche / Boden"),
        ),
        migrations.AddField(
            model_name="defect",
            name="accessory",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="defects", to="playgrounds.playgroundaccessory", verbose_name="Zusatzausstattung"),
        ),
        migrations.AddField(
            model_name="defect",
            name="source_type",
            field=models.CharField(choices=[("inspection", "Inspection"), ("citizen_report", "Citizen report"), ("internal_report", "Internal report"), ("maintenance", "Maintenance / care"), ("other", "Other")], default="internal_report", max_length=30, verbose_name="Quelle"),
        ),
        migrations.AddField(
            model_name="defect",
            name="reported_at",
            field=models.DateTimeField(default=timezone.now, verbose_name="Gemeldet am"),
        ),
        migrations.AddField(
            model_name="defect",
            name="reported_by_text",
            field=models.CharField(blank=True, default="", help_text="Optionaler Freitext, z. B. Bürgerin, Hauswart, Werkhof.", max_length=255, verbose_name="Gemeldet durch"),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="defect",
            name="urgency",
            field=models.CharField(blank=True, choices=[("a_immediate", "A (immediate)"), ("b_medium_term", "B (medium-term)")], default="", help_text="Nur erfassen, wenn ein Sicherheitsrisiko besteht.", max_length=30, verbose_name="Dringlichkeit"),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="defect",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, default=timezone.now, verbose_name="Aktualisiert am"),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="defect",
            name="inspection",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="defects", to="inspections.inspection", verbose_name="Kontrolle"),
        ),
        migrations.AlterField(
            model_name="defect",
            name="equipment",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="defects", to="playgrounds.playequipment", verbose_name="Spielgerät"),
        ),
        migrations.AlterField(
            model_name="defect",
            name="internal_description",
            field=models.TextField(verbose_name="Interne Beschreibung"),
        ),
        migrations.AlterField(
            model_name="defect",
            name="internal_note",
            field=models.TextField(blank=True, verbose_name="Interne Notiz"),
        ),
        migrations.AlterField(
            model_name="defect",
            name="has_safety_risk",
            field=models.BooleanField(default=False, verbose_name="Sicherheitsrisiko"),
        ),
        migrations.AlterField(
            model_name="defect",
            name="planned_resolution_date",
            field=models.DateField(blank=True, null=True, verbose_name="Geplante Behebung"),
        ),
        migrations.AlterField(
            model_name="defect",
            name="public_visible",
            field=models.BooleanField(default=False, verbose_name="Öffentlich sichtbar"),
        ),
        migrations.AlterField(
            model_name="defect",
            name="public_note",
            field=models.TextField(blank=True, verbose_name="Öffentlicher Hinweis"),
        ),
        migrations.AlterField(
            model_name="defectimage",
            name="caption",
            field=models.CharField(blank=True, max_length=255, verbose_name="Bildlegende"),
        ),
        migrations.AlterField(
            model_name="defectimage",
            name="public_visible",
            field=models.BooleanField(default=False, verbose_name="Öffentlich sichtbar"),
        ),
        migrations.AddField(
            model_name="defectimage",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, default=timezone.now, verbose_name="Erstellt am"),
            preserve_default=False,
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
            field=models.DateField(blank=True, null=True, verbose_name="Geplant am"),
        ),
        migrations.AlterField(
            model_name="maintenanceaction",
            name="completed_date",
            field=models.DateField(blank=True, null=True, verbose_name="Abgeschlossen am"),
        ),
        migrations.AlterField(
            model_name="maintenanceaction",
            name="public_visible",
            field=models.BooleanField(default=False, verbose_name="Öffentlich sichtbar"),
        ),
        migrations.AddField(
            model_name="maintenanceaction",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, default=timezone.now, verbose_name="Aktualisiert am"),
            preserve_default=False,
        ),
        migrations.AlterModelOptions(
            name="defect",
            options={"ordering": ["-has_safety_risk", "planned_resolution_date", "-created_at"], "verbose_name": "Mangel", "verbose_name_plural": "Mängel"},
        ),
        migrations.AlterModelOptions(
            name="defectimage",
            options={"ordering": ["created_at"], "verbose_name": "Mangelbild", "verbose_name_plural": "Mangelbilder"},
        ),
        migrations.AlterModelOptions(
            name="inspectionanswer",
            options={"ordering": ["scope__sort_order", "criterion__area", "criterion__title"], "verbose_name": "Prüfantwort", "verbose_name_plural": "Prüfantworten"},
        ),
        migrations.AlterModelOptions(
            name="maintenanceaction",
            options={"ordering": ["planned_date", "-created_at"], "verbose_name": "Instandhaltungsmassnahme", "verbose_name_plural": "Instandhaltungsmassnahmen"},
        ),
    ]
