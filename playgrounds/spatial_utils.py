import json

from django.contrib.gis.geos import GEOSGeometry, MultiPolygon, Point, Polygon

from .geo_constants import LV95_SRID


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
