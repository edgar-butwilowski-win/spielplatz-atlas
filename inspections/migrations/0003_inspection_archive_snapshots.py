# Generated manually for SpielplatzAtlas.

from django.db import migrations, models


def populate_archive_snapshots(apps, schema_editor):
    Inspection = apps.get_model("inspections", "Inspection")
    InspectionScope = apps.get_model("inspections", "InspectionScope")
    InspectionAnswer = apps.get_model("inspections", "InspectionAnswer")

    for inspection in Inspection.objects.select_related("playground", "playground__organization").iterator():
        playground = inspection.playground
        inspection.playground_name_snapshot = playground.name if playground else ""
        inspection.organization_name_snapshot = playground.organization.name if playground and playground.organization_id else ""
        inspection.save(update_fields=["playground_name_snapshot", "organization_name_snapshot"])

    for scope in InspectionScope.objects.select_related(
        "equipment",
        "equipment__equipment_type",
        "surface",
        "accessory",
    ).iterator():
        scope.label_snapshot = scope.label or ""
        if scope.equipment_id:
            scope.equipment_name_snapshot = scope.equipment.name or ""
            scope.equipment_inventory_number_snapshot = scope.equipment.inventory_number or ""
            scope.equipment_type_snapshot = scope.equipment.equipment_type.name if scope.equipment.equipment_type_id else ""
        if scope.surface_id:
            scope.surface_name_snapshot = scope.surface.name or ""
        if scope.accessory_id:
            scope.accessory_name_snapshot = scope.accessory.name or ""
        scope.save(
            update_fields=[
                "label_snapshot",
                "equipment_name_snapshot",
                "equipment_inventory_number_snapshot",
                "equipment_type_snapshot",
                "surface_name_snapshot",
                "accessory_name_snapshot",
            ]
        )

    for answer in InspectionAnswer.objects.select_related("criterion", "inspection").prefetch_related("defects").iterator(chunk_size=1000):
        criterion = answer.criterion
        answer.criterion_area_snapshot = criterion.area or ""
        answer.criterion_title_snapshot = criterion.title or ""
        answer.criterion_inspection_text_snapshot = criterion.inspection_text or ""
        answer.criterion_maintenance_text_snapshot = criterion.maintenance_text or ""
        answer.criterion_norm_reference_snapshot = criterion.norm_reference or ""
        if answer.inspection.status == "completed":
            answer.defect_summary_snapshot = ", ".join(
                f"#{defect.id} {defect.get_status_display()}" for defect in answer.defects.order_by("id")
            )
        answer.save(
            update_fields=[
                "criterion_area_snapshot",
                "criterion_title_snapshot",
                "criterion_inspection_text_snapshot",
                "criterion_maintenance_text_snapshot",
                "criterion_norm_reference_snapshot",
                "defect_summary_snapshot",
            ]
        )


class Migration(migrations.Migration):

    dependencies = [
        ("inspections", "0002_defect_status_canceled"),
    ]

    operations = [
        migrations.AddField(
            model_name="inspection",
            name="organization_name_snapshot",
            field=models.CharField(blank=True, max_length=255, verbose_name="Archiv: Organisation"),
        ),
        migrations.AddField(
            model_name="inspection",
            name="playground_name_snapshot",
            field=models.CharField(blank=True, max_length=255, verbose_name="Archiv: Spielplatz"),
        ),
        migrations.AddField(
            model_name="inspectionscope",
            name="accessory_name_snapshot",
            field=models.CharField(blank=True, max_length=255, verbose_name="Archiv: Zusatzausstattung"),
        ),
        migrations.AddField(
            model_name="inspectionscope",
            name="equipment_inventory_number_snapshot",
            field=models.CharField(blank=True, max_length=100, verbose_name="Archiv: Inventarnummer"),
        ),
        migrations.AddField(
            model_name="inspectionscope",
            name="equipment_name_snapshot",
            field=models.CharField(blank=True, max_length=255, verbose_name="Archiv: Spielgerät"),
        ),
        migrations.AddField(
            model_name="inspectionscope",
            name="equipment_type_snapshot",
            field=models.CharField(blank=True, max_length=255, verbose_name="Archiv: Spielgerätetyp"),
        ),
        migrations.AddField(
            model_name="inspectionscope",
            name="label_snapshot",
            field=models.CharField(blank=True, max_length=255, verbose_name="Archiv: Bezeichnung"),
        ),
        migrations.AddField(
            model_name="inspectionscope",
            name="surface_name_snapshot",
            field=models.CharField(blank=True, max_length=255, verbose_name="Archiv: Fallschutzfläche / Boden"),
        ),
        migrations.AddField(
            model_name="inspectionanswer",
            name="criterion_area_snapshot",
            field=models.CharField(blank=True, max_length=255, verbose_name="Archiv: Bereich"),
        ),
        migrations.AddField(
            model_name="inspectionanswer",
            name="criterion_inspection_text_snapshot",
            field=models.TextField(blank=True, verbose_name="Archiv: Prüfhinweis"),
        ),
        migrations.AddField(
            model_name="inspectionanswer",
            name="criterion_maintenance_text_snapshot",
            field=models.TextField(blank=True, verbose_name="Archiv: Wartungshinweis"),
        ),
        migrations.AddField(
            model_name="inspectionanswer",
            name="criterion_norm_reference_snapshot",
            field=models.CharField(blank=True, max_length=255, verbose_name="Archiv: Norm-/Quellenhinweis"),
        ),
        migrations.AddField(
            model_name="inspectionanswer",
            name="criterion_title_snapshot",
            field=models.CharField(blank=True, max_length=255, verbose_name="Archiv: Prüfkriterium"),
        ),
        migrations.AddField(
            model_name="inspectionanswer",
            name="defect_summary_snapshot",
            field=models.TextField(blank=True, verbose_name="Archiv: Mängel zum Abschlusszeitpunkt"),
        ),
        migrations.RunPython(populate_archive_snapshots, migrations.RunPython.noop),
    ]
