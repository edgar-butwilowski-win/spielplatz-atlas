# Generated manually to align quartier GeoJSON field metadata

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("playgrounds", "0013_spatialite_geometry"),
    ]

    operations = [
        migrations.AlterField(
            model_name="quartier",
            name="geom",
            field=models.JSONField(
                help_text="Importierte GeoJSON-Geometrie des Quartiers. Erwartet Polygon oder MultiPolygon in LV95-Koordinaten.",
                verbose_name="GeoJSON-Geometrie",
            ),
        ),
    ]
