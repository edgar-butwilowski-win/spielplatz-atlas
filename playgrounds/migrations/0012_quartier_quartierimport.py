# Generated manually for quartier import support

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("playgrounds", "0011_supplier_contacts_equipment_inspection_flags"),
        ("tenants", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Quartier",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=200, verbose_name="Quartiername")),
                ("geom", models.JSONField(help_text="GeoJSON-Geometrie des Quartiers. Erwartet Polygon oder MultiPolygon in LV95-Koordinaten.", verbose_name="Geometrie")),
                ("source", models.CharField(blank=True, max_length=500, verbose_name="Quelle")),
                ("is_active", models.BooleanField(default=True, verbose_name="Aktiv")),
                ("imported_at", models.DateTimeField(auto_now=True, verbose_name="Importiert am")),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="quartiere", to="tenants.organization", verbose_name="Organisation")),
            ],
            options={
                "verbose_name": "Quartier",
                "verbose_name_plural": "Quartiere",
                "ordering": ["organization__name", "name"],
                "unique_together": {("organization", "name")},
            },
        ),
        migrations.CreateModel(
            name="QuartierImport",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("geojson_file", models.FileField(blank=True, help_text="Optional. Erwartet FeatureCollection mit Quartiername und Geometrie/geom.", upload_to="quartier_imports/", verbose_name="GeoJSON-Datei")),
                ("wfs_endpoint", models.URLField(blank=True, help_text="Optional. Zum Beispiel ein GetCapabilities-Endpoint eines WFS.", max_length=1000, verbose_name="WFS-Endpoint")),
                ("replace_existing", models.BooleanField(default=False, verbose_name="Bestehende Quartiere dieser Organisation vor Import deaktivieren")),
                ("last_import_message", models.TextField(blank=True, verbose_name="Letzte Importmeldung")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Erstellt am")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Aktualisiert am")),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="quartier_imports", to="tenants.organization", verbose_name="Organisation")),
            ],
            options={
                "verbose_name": "Quartier-Import",
                "verbose_name_plural": "Quartier-Importe",
                "ordering": ["-updated_at"],
            },
        ),
    ]
