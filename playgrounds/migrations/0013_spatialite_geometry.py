# Generated manually for SpatiaLite geometry support

import json

import django.contrib.gis.db.models.fields
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon, Point, Polygon
from django.db import migrations


LV95_SRID = 2056


def point_from_lv95(x, y):
    if x is None or y is None:
        return None
    return Point(float(x), float(y), srid=LV95_SRID)


def multipolygon_from_geojson(geometry):
    if not geometry:
        return None

    geos_geometry = GEOSGeometry(json.dumps(geometry), srid=LV95_SRID)

    if isinstance(geos_geometry, Polygon):
        return MultiPolygon(geos_geometry, srid=LV95_SRID)

    if isinstance(geos_geometry, MultiPolygon):
        geos_geometry.srid = LV95_SRID
        return geos_geometry

    return None


def populate_spatial_geometries(apps, schema_editor):
    Playground = apps.get_model("playgrounds", "Playground")
    PlayEquipment = apps.get_model("playgrounds", "PlayEquipment")
    Quartier = apps.get_model("playgrounds", "Quartier")

    for playground in Playground.objects.exclude(longitude__isnull=True).exclude(latitude__isnull=True):
        playground.location = point_from_lv95(playground.longitude, playground.latitude)
        playground.save(update_fields=["location"])

    for equipment in PlayEquipment.objects.exclude(longitude__isnull=True).exclude(latitude__isnull=True):
        equipment.location = point_from_lv95(equipment.longitude, equipment.latitude)
        equipment.save(update_fields=["location"])

    for quartier in Quartier.objects.all():
        quartier.geometry = multipolygon_from_geojson(quartier.geom)
        quartier.save(update_fields=["geometry"])


def clear_spatial_geometries(apps, schema_editor):
    Playground = apps.get_model("playgrounds", "Playground")
    PlayEquipment = apps.get_model("playgrounds", "PlayEquipment")
    Quartier = apps.get_model("playgrounds", "Quartier")

    Playground.objects.update(location=None)
    PlayEquipment.objects.update(location=None)
    Quartier.objects.update(geometry=None)


class Migration(migrations.Migration):

    dependencies = [
        ("playgrounds", "0012_quartier_quartierimport"),
    ]

    operations = [
        migrations.AddField(
            model_name="playground",
            name="location",
            field=django.contrib.gis.db.models.fields.PointField(
                blank=True,
                help_text="Aus LV95 X/Y abgeleiteter Punkt für räumliche Abfragen mit SpatiaLite.",
                null=True,
                srid=LV95_SRID,
                verbose_name="Lagegeometrie",
            ),
        ),
        migrations.AddField(
            model_name="playequipment",
            name="location",
            field=django.contrib.gis.db.models.fields.PointField(
                blank=True,
                help_text="Aus LV95 X/Y abgeleiteter Punkt für räumliche Abfragen mit SpatiaLite.",
                null=True,
                srid=LV95_SRID,
                verbose_name="Lagegeometrie",
            ),
        ),
        migrations.AddField(
            model_name="quartier",
            name="geometry",
            field=django.contrib.gis.db.models.fields.MultiPolygonField(
                blank=True,
                help_text="Aus GeoJSON abgeleitete MultiPolygon-Geometrie für räumliche Abfragen mit SpatiaLite.",
                null=True,
                srid=LV95_SRID,
                verbose_name="Geometrie",
            ),
        ),
        migrations.RunPython(populate_spatial_geometries, clear_spatial_geometries),
    ]
